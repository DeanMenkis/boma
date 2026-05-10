from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "success", "message": "BOMA Backend is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/test-search")
def test_search(part_name: str = "resistor", quantity: int = 1):
    return {
        "query": {"part_name": part_name, "quantity": quantity},
        "results": [
            {"id": "mock-1", "name": f"{part_name} 10k", "price": 0.05},
            {"id": "mock-2", "name": f"{part_name} 100k", "price": 0.07}
        ]
    }

@app.post("/test-bom")
def test_bom(data: dict):
    return {
        "received": data,
        "message": "BOM data received successfully",
        "item_count": len(data.get("items", []))
    }
