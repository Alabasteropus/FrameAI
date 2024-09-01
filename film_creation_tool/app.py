from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.websockets import WebSocketDisconnect
from pydantic import BaseModel
import psycopg
import os
import io
from frameioclient import FrameioClient
from typing import Optional, List
from enum import Enum
from datetime import datetime

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Frame.io API setup
FRAMEIO_TOKEN = os.environ.get("FrameAPI")
if not FRAMEIO_TOKEN:
    raise ValueError("Frame.io API token not found in environment variables")

frameio_client = FrameioClient(FRAMEIO_TOKEN)

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    genre: Optional[str] = None
    director: Optional[str] = None
    producer: Optional[str] = None

class FileType(str, Enum):
    SCRIPT = "script"
    MEDIA = "media"

class FileUpload(BaseModel):
    file_type: FileType
    tags: Optional[List[str]] = None

class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ShotCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration: Optional[float] = None

class ShotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None
    order: Optional[int] = None

class ShotOrder(BaseModel):
    shot_ids: List[str]

class ShareProject(BaseModel):
    project_id: str
    email: str
    permission: str

class Comment(BaseModel):
    asset_id: str
    text: str
    timestamp: Optional[datetime] = None

class Approval(BaseModel):
    asset_id: str
    status: str  # e.g., "approved", "rejected", "needs_review"
    reviewer: str

class ExportRequest(BaseModel):
    asset_id: str
    format: str  # e.g., "mp4", "mov"
    quality: Optional[str] = "high"  # e.g., "low", "medium", "high"

class DirectShareRequest(BaseModel):
    asset_id: str
    email: str
    permission: str  # e.g., "view", "review", "collaborate"

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/frameio-connection")
async def test_frameio_connection():
    try:
        # Test the connection by fetching the current user's info
        user = frameio_client.get_me()
        return {"status": "connected", "user": user['email']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Frame.io API: {str(e)}")

@app.post("/projects")
async def create_project(project: ProjectCreate):
    try:
        # Create a new project in Frame.io
        new_project = frameio_client.create_project(
            name=project.name,
            private=True
        )

        # Update project with additional metadata
        updated_project = frameio_client.update_project(
            project_id=new_project['id'],
            **project.dict(exclude_unset=True)
        )

        return {"status": "success", "project": updated_project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@app.post("/projects/{project_id}/upload")
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    tags: Optional[str] = Form(None)
):
    try:
        # Get the root asset of the project
        root_asset = frameio_client.get_project(project_id)['root_asset_id']

        # Upload the file to Frame.io
        asset = frameio_client.upload(
            parent_asset_id=root_asset,
            file=file.file,
            file_name=file.filename
        )

        # Add metadata (tags) to the asset
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            frameio_client.update_asset(
                asset_id=asset['id'],
                tags=tag_list
            )

        # Organize the asset based on file type
        if file_type == FileType.SCRIPT:
            script_folder = get_or_create_folder(project_id, "Scripts")
            frameio_client.move_asset(asset['id'], script_folder['id'])
        elif file_type == FileType.MEDIA:
            media_folder = get_or_create_folder(project_id, "Media")
            frameio_client.move_asset(asset['id'], media_folder['id'])

        return {"status": "success", "asset": asset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

def get_or_create_folder(project_id: str, folder_name: str):
    root_asset = frameio_client.get_project(project_id)['root_asset_id']
    assets = frameio_client.get_assets(root_asset)

    for asset in assets:
        if asset['type'] == 'folder' and asset['name'] == folder_name:
            return asset

    # If folder doesn't exist, create it
    return frameio_client.create_asset(
        parent_asset_id=root_asset,
        name=folder_name,
        type='folder'
    )

# Sequence and Shot management functions
def create_sequence(project_id: str, name: str):
    sequences_folder = get_or_create_folder(project_id, "Sequences")
    return frameio_client.create_asset(
        parent_asset_id=sequences_folder['id'],
        name=name,
        type='folder'
    )

def create_shot(sequence_id: str, shot: ShotCreate):
    asset = frameio_client.create_asset(
        parent_asset_id=sequence_id,
        name=shot.name,
        type='file'
    )

    # Update asset with additional metadata
    updated_asset = frameio_client.update_asset(
        asset_id=asset['id'],
        description=shot.description,
        properties={
            'duration': shot.duration
        }
    )

    return updated_asset

def reorder_shots(sequence_id: str, shot_ids: List[str]):
    return frameio_client.reorder_assets(sequence_id, shot_ids)

# API endpoints for sequence and shot management
@app.post("/projects/{project_id}/sequences")
async def create_sequence_endpoint(project_id: str, sequence: SequenceCreate):
    try:
        new_sequence = create_sequence(project_id, sequence.name)
        return {"status": "success", "sequence": new_sequence}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sequence: {str(e)}")

@app.post("/sequences/{sequence_id}/shots")
async def create_shot_endpoint(sequence_id: str, shot: ShotCreate):
    try:
        new_shot = create_shot(sequence_id, shot.name)
        # Update shot with additional metadata
        updated_shot = frameio_client.update_asset(
            asset_id=new_shot['id'],
            description=shot.description,
            properties={
                'duration': shot.duration
            }
        )
        return {"status": "success", "shot": updated_shot}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create shot: {str(e)}")

@app.put("/sequences/{sequence_id}/reorder")
async def reorder_shots_endpoint(sequence_id: str, shot_order: ShotOrder):
    try:
        # Verify that the sequence exists
        sequence = frameio_client.get_asset(sequence_id)
        if sequence['type'] != 'folder':
            raise HTTPException(status_code=400, detail="Invalid sequence ID")

        # Get all shots in the sequence
        shots = frameio_client.get_assets(sequence_id)
        shot_ids = [shot['id'] for shot in shots if shot['type'] == 'file']

        # Verify that all provided shot IDs exist in the sequence
        if not all(shot_id in shot_ids for shot_id in shot_order.shot_ids):
            raise HTTPException(status_code=400, detail="Invalid shot ID provided")

        result = reorder_shots(sequence_id, shot_order.shot_ids)
        return JSONResponse(content={"status": "success", "result": result})
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reorder shots: {str(e)}")

# Collaboration features

from fastapi import BackgroundTasks
from fastapi.websockets import WebSocket

class ShareProject(BaseModel):
    project_id: str
    email: str
    permission: str

class Comment(BaseModel):
    asset_id: str
    text: str

class Approval(BaseModel):
    asset_id: str
    status: str

@app.post("/projects/{project_id}/share")
async def share_project(project_id: str, share: ShareProject):
    try:
        result = frameio_client.share_project(
            project_id=project_id,
            email=share.email,
            permission=share.permission
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share project: {str(e)}")

@app.post("/assets/{asset_id}/comment")
async def add_comment(asset_id: str, comment: Comment):
    try:
        result = frameio_client.create_comment(
            asset_id=asset_id,
            text=comment.text
        )
        return {"status": "success", "comment": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")

@app.post("/assets/{asset_id}/approve")
async def approve_asset(asset_id: str, approval: Approval):
    try:
        result = frameio_client.update_asset(
            asset_id=asset_id,
            status=approval.status
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update approval status: {str(e)}")

# WebSocket connection for real-time notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()

            # Process the received data (e.g., subscribe to specific project updates)
            # This is a placeholder and should be replaced with actual logic
            project_id = data  # Assuming the client sends a project_id

            # Simulate checking for updates (replace with actual Frame.io API calls)
            updates = await check_for_updates(project_id)

            # Send updates to the client
            await websocket.send_json({"message": "Update received", "data": updates})
    except WebSocketDisconnect:
        print("WebSocket disconnected")

async def check_for_updates(project_id: str):
    # This function should be implemented to check for updates in Frame.io
    # It could involve polling the Frame.io API or integrating with webhooks
    # For now, we'll return a placeholder update
    return {"project_id": project_id, "update_type": "new_comment"}

# Background task to handle notifications
async def send_notification(user_id: str, message: str):
    # TODO: Implement actual notification logic (e.g., email, push notification)
    print(f"Sending notification to user {user_id}: {message}")

@app.post("/webhook")
async def frame_io_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    event_type = payload.get('type')
    resource = payload.get('resource', {})

    if event_type == 'comment.created':
        asset_id = resource.get('asset_id')
        comment_text = resource.get('text')
        user_id = resource.get('user_id')
        background_tasks.add_task(send_notification, user_id, f"New comment on asset {asset_id}: {comment_text}")
    elif event_type == 'review.updated':
        asset_id = resource.get('asset_id')
        status = resource.get('status')
        user_id = resource.get('user_id')
        background_tasks.add_task(send_notification, user_id, f"Review status updated for asset {asset_id}: {status}")

    return {"status": "Webhook processed"}

# Export and Sharing Capabilities

class ExportRequest(BaseModel):
    asset_id: str
    format: str  # e.g., "mp4", "mov"

class DirectShareRequest(BaseModel):
    asset_id: str
    email: str
    permission: str

@app.post("/export")
async def export_asset(export_request: ExportRequest):
    try:
        asset = frameio_client.get_asset(export_request.asset_id)

        # Check if the asset is a sequence (folder) or a single file
        if asset['type'] == 'folder':
            # For sequences, we need to create a copy with all its contents
            exported_asset = frameio_client.copy_asset(export_request.asset_id)
        else:
            # For single files, we can use the original asset
            exported_asset = asset

        # Initiate the export process
        export_job = frameio_client.create_asset_export_job(
            asset_id=exported_asset['id'],
            format=export_request.format
        )

        return {"status": "success", "export_job": export_job}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export asset: {str(e)}")

@app.post("/share")
async def share_asset(share_request: DirectShareRequest):
    try:
        # Share the asset directly through Frame.io
        share_result = frameio_client.share_asset(
            asset_id=share_request.asset_id,
            email=share_request.email,
            permission=share_request.permission
        )

        return {"status": "success", "share_result": share_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share asset: {str(e)}")

@app.get("/export/{job_id}")
async def get_export_status(job_id: str):
    try:
        job_status = frameio_client.get_asset_export_job(job_id)
        return {"status": "success", "job_status": job_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get export job status: {str(e)}")
