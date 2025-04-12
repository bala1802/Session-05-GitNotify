import os
from dotenv import load_dotenv

load_dotenv()

import git

import time
import shutil

from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
import sys
import subprocess

import email_activities_helper
from datetime import datetime

from pathlib import Path
import git_activities_helper

mcp = FastMCP("Gmail MCP")

# Function to get formatted current time
def get_timestamp():
    return datetime.now().strftime("%d-%m-%Y, %H-%M-%S")

@mcp.tool()
def show_reasoning(steps: list) -> TextContent:
    """
    Displays the step-by-step reasoning process used in a given task.

    This tool prints each step in the reasoning chain to the console, helping developers or
    users understand how decisions were made or how a sequence of operations unfolded.

    Args:
        steps (list): A list of reasoning steps as strings, where each entry represents
                      one step in the decision-making or execution process.

    Returns:
        str: A confirmation message indicating the reasoning steps were displayed.

    Behavior:
        - Iterates over the list of reasoning steps.
        - Logs each step to the console in a numbered format for better readability.

    Example:
        >>> show_reasoning([
                "Started cloning the repository.",
                "Verified repository folder exists.",
                "Pull the code changes from the repository.",
                "Verified the latest pull status.",
                "Email notification sent.",
                Verified whether Email sent successfully or not.
            ])
        # Output:
        # ----------- Step 1 - Started cloning the repository. ------------
        # ----------- Step 2 - Verified repository folder exists. ------------
        # ----------- Step 3 - Pull the code changes from the repository. ------------
        # ----------- Step 4 - Verified the latest pull status. ------------
        # ----------- Step 5 - Email notification sent. ------------
        # ----------- Step 6 - Verified whether Email sent successfully or not. ------------

    Notes:
        - This tool is primarily for debugging and traceability.
        - Output is written to the console; it is not returned in the response text.
    """
    print(get_timestamp(), " MCP Server - Show the reasoning steps Tools is called")
    for i, step in enumerate(steps, 1):
        print(f"----------- Step {i} - {step} ------------")
    return TextContent(
        type="text",
        text="Reasoning shown"
    )

@mcp.tool()
def clone_repo(repo_url: str) -> TextContent:
    """
    Clones a GitHub repository to a specified directory.
    
    Args:
        repo_url (str): The URL of the GitHub repository to clone.
    
    Returns:
        str: The directory path where the repository is cloned.
    """
    print(get_timestamp(), " MCP Server - Clone Repository Tool is called")
    
    clone_dir = os.getcwd() + "/repository"
    if not os.path.exists(clone_dir):
        git.Repo.clone_from(repo_url, clone_dir)
        print(f"Repository cloned into {clone_dir}")
    else:
        print(f"Directory {clone_dir} already exists. Skipping clone.")
    
    return TextContent(
        type="text",
        text=clone_dir
    )

@mcp.tool()
def pull_repo(repo_dir: str) -> TextContent:
    """
    Pulls the latest changes from the specified repository.
    
    Args:
        repo_dir (str): The local directory path of the repository.
    
    Returns:
        str: "Changed" if new updates were pulled, "NoChanges" if the repository is up-to-date.
    """
    print(get_timestamp(), " MCP Server - Pull Repostory Tool is called")

    repo = git.Repo(repo_dir)
    origin = repo.remotes.origin
    fetch_info = origin.pull()
    
    if any(info.flags & git.FetchInfo.HEAD_UPTODATE == 0 for info in fetch_info):
        print(get_timestamp(), " MCP Server - Repository updated with the latest changes.")
        text = "Changed"
    else:
        print(get_timestamp(), " MCP Server - Nochanges detected.")
        text = "NoChanges"
    
    return TextContent(
        type="text",
        text=text
    )

@mcp.tool()
def send_email(message) -> TextContent:
    """
    Sends an email with the given message to a configured recipient.

    This function authenticates the email service and, if successful, 
    sends an email using the `email_activities_helper` module.

    Parameters:
    message (str): The content of the email to be sent.

    Returns:
    str: A response indicating success or failure.
    
    Errors:
    - Prints an error message and returns 'Authentication Failed' if authentication fails.
    
    Environment Variables:
    - RECEIVER_EMAIL_ID: The recipient's email address, retrieved from the environment.
    """

    print(get_timestamp(), " Proceedding with Email Activities")
    service = email_activities_helper.authenticate()
    print(get_timestamp(), " Authentication Called and the Service is : ", service)
    if service:
        text = email_activities_helper.send_email(service, to_email=os.environ["RECEIVER_EMAIL_ID"], subject="Message from GMail MCP Server", message_text=message)
    else:
        print("ERROR ")
        text = 'Authentication Failed'
    
    return TextContent(
        type="text",
        text=text
    )

@mcp.tool()
def verify(result: str) -> TextContent:
    """
    Verifies the outcome of a previously executed MCP tool action by evaluating the 
    result string and checking the corresponding system or service state.

    Based on the type of result provided (e.g., a file path, a git operation status, or
    an email confirmation), this method determines whether the intended action was 
    successfully completed.

    Args:
        result (str): A string representing the output of a previous MCP tool.
                      - If it's a file path, it's assumed to be the result of a `clone_repo` call.
                      - If it's "Changed" or "NoChanges", it's from `pull_repo`.
                      - If it contains "Email sent successfully", it's from `send_email`.

    Returns:
        str: "Verification Passed" if the corresponding state confirms success;
             otherwise, "Verification Failed".

    Verification Logic:
        - **Repository Clone**: If the result is a valid directory path, checks whether 
          the directory exists on disk.
        
        - **Repository Pull**: If the result is "Changed" or "NoChanges", confirms by 
          inspecting the latest git log using `git_activities_helper.get_git_log()`.

        - **Email Sent**: If the result contains "Email sent successfully", verifies the email
          was sent by checking the sent items via `email_activities_helper.was_email_sent()`.

    Notes:
        - Assumes use of `is_probable_path()` to determine if a result is a valid path.
        - Depends on helper modules for git log checks and email verification.
        - The subject line used for email verification is hardcoded as:
          "Message from GMail MCP Server".
    """

    if is_probable_path(result):
        verification_result = True if os.path.isdir(result) else False
    elif result == "Changed" or result == "NoChanges" :
        log = git_activities_helper.get_git_log()
        verification_result = True if "pull" in log else False
    else:
        service = email_activities_helper.authenticate()
        subject = "Message from GMail MCP Server"
        email_sent_verification_status = email_activities_helper.was_email_sent(service=service, to_email="pybot1802@gmail.com", subject_filter=subject)
        verification_result = True if "Email was sent successfully" in email_sent_verification_status else False
    
    verification_result = "✅✅✅✅✅✅✅ Verification Passed ✅✅✅✅✅✅✅" if verification_result else "❌❌❌❌❌❌❌ Verification Failed ❌❌❌❌❌❌❌"
    return TextContent(
        type="text",
        text=verification_result
    )

def is_probable_path(s):
    try:
        p = Path(s)
        # Consider it a path if it has at least one parent directory or a suffix
        return p.parent != Path('.') or p.suffix != ''
    except Exception:
        return False


if __name__ == "__main__":
    # Check if running with mcp dev command
    print(get_timestamp(), " Gmail MCP Server - STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution