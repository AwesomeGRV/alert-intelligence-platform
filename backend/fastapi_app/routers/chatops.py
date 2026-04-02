from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import structlog

from ..core.database import get_db
from ..services.chatops_service import ChatOpsService
from ..services.slack_service import SlackService
from ..services.teams_service import TeamsService

logger = structlog.get_logger()
router = APIRouter()
chatops_service = ChatOpsService()
slack_service = SlackService()
teams_service = TeamsService()

@router.post("/slack/events")
async def handle_slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()
        
        # Verify Slack request
        if not await slack_service.verify_request(request):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Handle URL verification for Slack
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        # Handle events
        if body.get("type") == "event_callback":
            event = body.get("event", {})
            
            if event.get("type") == "message" and not event.get("bot_id"):
                background_tasks.add_task(
                    process_slack_message,
                    event,
                    db
                )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Failed to handle Slack event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slack/commands")
async def handle_slack_commands(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        form_data = await request.form()
        
        # Verify Slack request
        if not await slack_service.verify_request(request):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        command = form_data.get("command")
        text = form_data.get("text", "")
        response_url = form_data.get("response_url")
        
        # Handle different commands
        if command == "/incident":
            background_tasks.add_task(
                handle_incident_command,
                text,
                response_url,
                db
            )
            return {"response_type": "in_progress"}
        
        elif command == "/alerts":
            background_tasks.add_task(
                handle_alerts_command,
                text,
                response_url,
                db
            )
            return {"response_type": "in_progress"}
        
        elif command == "/status":
            background_tasks.add_task(
                handle_status_command,
                text,
                response_url,
                db
            )
            return {"response_type": "in_progress"}
        
        else:
            return {
                "response_type": "ephemeral",
                "text": f"Unknown command: {command}"
            }
        
    except Exception as e:
        logger.error(f"Failed to handle Slack command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/teams/webhook")
async def handle_teams_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()
        
        # Handle Teams messages
        if body.get("type") == "message":
            background_tasks.add_task(
                process_teams_message,
                body,
                db
            )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Failed to handle Teams webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Command handlers
async def handle_incident_command(text: str, response_url: str, db: AsyncSession):
    try:
        parts = text.strip().split()
        if not parts:
            response = {
                "response_type": "ephemeral",
                "text": "Usage: /incident <action> [incident_id]\nActions: explain, list, resolve"
            }
        else:
            action = parts[0]
            incident_id = parts[1] if len(parts) > 1 else None
            
            if action == "explain" and incident_id:
                response = await chatops_service.explain_incident(incident_id, db)
            elif action == "list":
                response = await chatops_service.list_incidents(db)
            elif action == "resolve" and incident_id:
                response = await chatops_service.resolve_incident(incident_id, db)
            else:
                response = {
                    "response_type": "ephemeral",
                    "text": "Invalid command. Usage: /incident <action> [incident_id]"
                }
        
        await slack_service.send_response(response_url, response)
        
    except Exception as e:
        logger.error(f"Failed to handle incident command: {str(e)}")
        error_response = {
            "response_type": "ephemeral",
            "text": f"Error: {str(e)}"
        }
        await slack_service.send_response(response_url, error_response)

async def handle_alerts_command(text: str, response_url: str, db: AsyncSession):
    try:
        parts = text.strip().split()
        if not parts:
            response = {
                "response_type": "ephemeral",
                "text": "Usage: /alerts <action> [service|severity]\nActions: list, recent, service"
            }
        else:
            action = parts[0]
            filter_value = parts[1] if len(parts) > 1 else None
            
            if action == "list":
                response = await chatops_service.list_alerts(db, filter_value)
            elif action == "recent":
                response = await chatops_service.recent_alerts(db)
            elif action == "service" and filter_value:
                response = await chatops_service.service_alerts(filter_value, db)
            else:
                response = {
                    "response_type": "ephemeral",
                    "text": "Invalid command. Usage: /alerts <action> [filter]"
                }
        
        await slack_service.send_response(response_url, response)
        
    except Exception as e:
        logger.error(f"Failed to handle alerts command: {str(e)}")
        error_response = {
            "response_type": "ephemeral",
            "text": f"Error: {str(e)}"
        }
        await slack_service.send_response(response_url, error_response)

async def handle_status_command(text: str, response_url: str, db: AsyncSession):
    try:
        response = await chatops_service.get_system_status(db)
        await slack_service.send_response(response_url, response)
        
    except Exception as e:
        logger.error(f"Failed to handle status command: {str(e)}")
        error_response = {
            "response_type": "ephemeral",
            "text": f"Error: {str(e)}"
        }
        await slack_service.send_response(response_url, error_response)

async def process_slack_message(event: Dict[str, Any], db: AsyncSession):
    try:
        # Process direct messages or mentions
        text = event.get("text", "")
        channel = event.get("channel")
        user = event.get("user")
        
        # Check if message contains incident-related keywords
        if any(keyword in text.lower() for keyword in ["incident", "alert", "issue", "problem"]):
            response = await chatops_service.process_message(text, db)
            await slack_service.send_message(channel, response)
        
    except Exception as e:
        logger.error(f"Failed to process Slack message: {str(e)}")

async def process_teams_message(body: Dict[str, Any], db: AsyncSession):
    try:
        # Process Teams messages
        text = body.get("text", "")
        conversation_id = body.get("conversation", {}).get("id")
        
        # Check if message contains incident-related keywords
        if any(keyword in text.lower() for keyword in ["incident", "alert", "issue", "problem"]):
            response = await chatops_service.process_message(text, db)
            await teams_service.send_message(conversation_id, response)
        
    except Exception as e:
        logger.error(f"Failed to process Teams message: {str(e)}")
