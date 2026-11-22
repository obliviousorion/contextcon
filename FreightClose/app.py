"""FastAPI adapter for the local settlement service."""
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

import service

app = FastAPI(title="FreightClose")


@app.exception_handler(service.ServiceError)
async def service_error(request: Request, error: service.ServiceError):
    return JSONResponse({"detail": error.detail}, status_code=error.status_code)


@app.get("/")
def home():
    return FileResponse(service.ROOT / "index.html")


app.get("/api/status")(service.status)
app.get("/api/sample")(service.get_sample)
app.get("/api/cases")(service.history)
app.post("/api/run")(service.run)
app.post("/api/cases/{rid}/resolve")(service.resolve)
app.post("/api/cases/{rid}/retry")(service.retry)


@app.get("/api/cases/{rid}/receipt")
def receipt(rid: str):
    result = service.receipt_data(rid)
    return JSONResponse(result, headers={"Content-Disposition": f'attachment; filename="freight-{result["id"]}.json"'})
