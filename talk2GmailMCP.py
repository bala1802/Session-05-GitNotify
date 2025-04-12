import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import google.generativeai as genai
import traceback
from datetime import datetime

import prompts

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Function to get formatted current time
def get_timestamp():
    return datetime.now().strftime("%d-%m-%Y, %H-%M-%S")

async def generate_with_timeout(prompt, timeout=10):
    """Generate content with a timeout"""
    print(get_timestamp(), "- [INFO] Starting LLM generation...")
    try:
        loop = asyncio.get_event_loop()
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=timeout
        )

        print(get_timestamp(), "- [SUCCESS] LLM generation completed.")
        return response

    except TimeoutError:
        print(get_timestamp(), "- [ERROR] LLM generation timed out!")
        raise
    except Exception as e:
        print(get_timestamp(), f"- [ERROR] Error in LLM generation: {e}")
        traceback.print_exc()
        raise

async def main():
    print(get_timestamp(), "- [INFO] Establishing connection to MCP server...")

    server_params = StdioServerParameters(command="python", args=["gmail_server.py"])
    async with stdio_client(server_params) as (read, write):
        print(get_timestamp(), "- [SUCCESS] Connection established, creating session...")

        async with ClientSession(read, write) as session:
            print(get_timestamp(), "- [INFO] Session created, initializing...")
            await session.initialize()

            # Get available tools
            print(get_timestamp(), "- [INFO] Requesting tool list...")
            tools_result = await session.list_tools()
            tools = tools_result.tools
            print(get_timestamp(), f"- [SUCCESS] Retrieved {len(tools)} tools.")

            # Process tools information
            tools_description = []
            for i, tool in enumerate(tools):
                try:
                    params = tool.inputSchema
                    desc = getattr(tool, 'description', 'No description available')
                    name = getattr(tool, 'name', f'tool_{i}')

                    params_str = ', '.join([f"{p}: {params['properties'][p]['type']}" 
                                            for p in params.get('properties', {})]) if 'properties' in params else 'no parameters'

                    tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                    tools_description.append(tool_desc)
                    print(get_timestamp(), f"- [INFO] Processed tool: {tool_desc}")
                except Exception as e:
                    print(get_timestamp(), f"- [ERROR] Error processing tool {i}: {e}")
                    tools_description.append(f"{i+1}. Error processing tool")

            available_tools = "\n".join(tools_description)

            system_prompt = prompts.system_prompt.format(available_tools=available_tools)

            # print("+++++++++++++++++++++++++++++")
            # print(system_prompt)
            # print("+++++++++++++++++++++++++++++")

            # sys.exit()

            max_iterations = 8
            last_response = None
            iteration = 1
            iteration_response = []
            url = "https://github.com/bala1802/test_repo"

            query = f"Clone this repository '{url}', take a pull and email the code changes."
            current_query = query  

            while iteration < max_iterations:
                print("\n" + get_timestamp(), f"- [INFO] --- Iteration {iteration} ---")

                for eachIterationResponse in iteration_response:
                    print("********************")
                    print(eachIterationResponse)
                
                if last_response is not None:
                    current_query += "\n\n" + " ".join(iteration_response) + "\n\n"
                    current_query += "\n\nWhat should I do next?"

                print(get_timestamp(), "- [INFO] Current Query:", current_query)

                prompt = f"{system_prompt}\n\nQuery: {current_query}"
                try:
                    response = await generate_with_timeout(prompt)
                    response_text = response.text.strip()

                    for line in response_text.split('\n'):
                        line = line.strip()
                        if line.startswith("FUNCTION_CALL:") or line.startswith("FUNCTION_CALL|"):
                            response_text = line
                            break
                
                except Exception as e:
                    print(get_timestamp(), f"- [ERROR] Failed to get LLM response: {e}")
                    traceback.print_exc()
                    break

                print(get_timestamp(), "- [INFO] Response from LLM:", response_text)

                if response_text.startswith("FUNCTION_CALL:") or response_text.startswith("FUNCTION_CALL|"):
                    _, function_info = response_text.split(":", 1) if response_text.startswith("FUNCTION_CALL:") else response_text.split("|", 1)
                    parts = [p.strip() for p in function_info.split("|")]
                    func_name, params = parts[0], parts[1:]

                    print(get_timestamp(), f"- [DEBUG] Parsed Function Call: {func_name} with parameters {params}")

                    try:
                        tool = next((t for t in tools if t.name == func_name), None)
                        if not tool:
                            raise ValueError(f"Unknown tool: {func_name}")

                        arguments = {}
                        schema_properties = tool.inputSchema.get('properties', {})
                        
                        for param_name, param_info in schema_properties.items():
                            if not params:
                                raise ValueError(f"Not enough parameters for {func_name}")
                                
                            value = params.pop(0)
                            param_type = param_info.get('type', 'string')

                            if param_type == 'integer':
                                arguments[param_name] = int(value)
                            elif param_type == 'number':
                                arguments[param_name] = float(value)
                            elif param_type == 'array':
                                value = value.strip('[]').split(',')
                                arguments[param_name] = [int(x.strip()) for x in value]
                            else:
                                arguments[param_name] = str(value)

                        print(get_timestamp(), f"- [INFO] Calling tool {func_name} with arguments {arguments}")

                        result = await session.call_tool(func_name, arguments=arguments)

                        # iteration_result = [item.text if hasattr(item, 'text') else str(item) for item in result.content] if hasattr(result, 'content') else str(result)
                        iteration_result = result.content[0].text if result.content and hasattr(result.content[0], 'text') else None

                        iteration_response.append(
                            f"Iteration {iteration}: Called {func_name} with {arguments}, result: {iteration_result}."
                        )
                        last_response = iteration_result
                        iteration += 1
                        
                    except Exception as e:
                        print(get_timestamp(), f"- [ERROR] Error in tool execution: {e}")
                        traceback.print_exc()
                        iteration_response.append(f"Error in iteration {iteration}: {str(e)}")
                        break

                elif response_text.startswith("FINAL_ANSWER:"):
                    print(get_timestamp(), "- [SUCCESS] AGENT EXECUTION COMPLETED.")
                    break

if __name__ == "__main__":
    asyncio.run(main())