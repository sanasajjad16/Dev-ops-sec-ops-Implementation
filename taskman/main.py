# -*- coding: utf-8 -*-
from uuid import uuid4
from typing import List
from os import getenv
from typing_extensions import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from redis import Redis
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
import fastapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI()


def redis_client():
    return Redis(host=getenv('REDIS_HOST', 'localhost'), port=6379, decode_responses=True)


class TaskRequest(BaseModel):
    name: str
    description: str


class Task(TaskRequest):
    id: str

# @app.get('/')
# def redirect_to_tasks() -> None:
# return {"message": "Hello Kashaf"}

@app.get('/')
def redirect_to_tasks() -> None:
    return RedirectResponse(url='/tasks')


@app.get('/tasks')
def get_tasks(redis: Annotated[Redis, Depends(redis_client)]) -> List[Task]:
    keys = redis.keys()

    tasks = []
    for key in keys:
        task = redis.json().get(key)
        task_id = key[6:]
       
    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag('task.id', task_id)

        tasks.append(Task(
            id=task_id,
            name=task['name'],
            description=task['description'],
        ))
    return tasks


@app.get('/tasks/{task_id}')
def get_task(task_id: str,
             redis: Annotated[Redis, Depends(redis_client)]) -> Task:
    task = redis.json().get(f'tasks:{task_id}')

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag('task.id', task_id)

    return Task(
        id=task_id,
        name=task['name'],
        description=task['description'],
    )


@app.put('/tasks/{item_id}')
def update_task(task_id: str,
                item: TaskRequest,
                redis: Annotated[Redis, Depends(redis_client)]) -> None:
    redis.json().set(f'tasks:{task_id}', {
        'name': item.name,
        'description': item.description,
    })


@app.post('/tasks')
def create_task(request: TaskRequest,
                redis: Annotated[Redis, Depends(redis_client)]) -> str:
    task_id = uuid4()
    redis.json().set(f'tasks:{task_id}', '$', {
        'name': request.name,
        'description': request.description,
    })
    return str(task_id)


provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

# Sets the global default tracer provider
trace.set_tracer_provider(provider)

# Creates a tracer from the global tracer provider
tracer = trace.get_tracer("my.tracer.name")

FastAPIInstrumentor.instrument_app(app)
