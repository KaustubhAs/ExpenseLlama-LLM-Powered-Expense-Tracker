from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from fastapi.middleware import Middleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from datetime import date
import pandas as pd
import plotly.express as px

from .database import SessionLocal, Transaction
from .llm_service import CategoryPredictor

# app = FastAPI(middleware=[
#     Middleware(HTTPSRedirectMiddleware),
# ])
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
predictor = CategoryPredictor()

@app.get("/")
async def home(request: Request):
    # This template simply shows the data entry form.
    # It does not reference a "charts" variable.
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/debug/categorization")
async def debug_categorization(description: str):
    category = predictor.predict_category(description)
    return {
        "input": description,
        "category": category,
        "model": "llama3.2"
    }

@app.get("/debug/categorization")
async def debug_categorization(description: str):
    category = predictor.predict_category(description)
    return {"description": description, "predicted_category": category}


@app.get("/health")
async def health_check():
    return {
        "status": "active",
        "llm_connected": True,
        "database_connections": 1
    }

@app.post("/add_transaction")
async def add_transaction(
    request: Request,
    description: str = Form(...),
    amount: float = Form(...),
    type: str = Form(...),
    transaction_date: date = Form(...)
):
     #Add validation checks
    if amount <= 0:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "message": "Amount must be positive"
        })
    if type not in ["Expense", "Income"]:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "message": "Invalid transaction type"
        })

    category = predictor.predict_category(description)
    db = SessionLocal()
    transaction = Transaction(
        date=transaction_date,
        description=description,
        type=type,
        amount=amount,
        category=category
    )
    db.add(transaction)
    db.commit()
    db.close()
    # After adding, redirect back to home or show a success message.
    return templates.TemplateResponse("index.html", {"request": request, "message": f"Added (Category: {category})"})

# Add this endpoint above the existing dashboard route (around line 56)
@app.get("/transactions")
async def get_transactions():
    db = SessionLocal()
    transactions = db.query(Transaction).all()
    db.close()
    
    return {
        "count": len(transactions),
        "transactions": [
            {
                "date": str(t.date),
                "description": t.description,
                "type": t.type,
                "amount": t.amount,
                "category": t.category
            } for t in transactions
        ]
    }


@app.get("/dashboard")
async def dashboard(request: Request):
    db = SessionLocal()
    transactions = db.query(Transaction).all()

    if not transactions:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "charts": {"error": "No transactions found"},
            "transactions": []
        })

    # Convert transactions to a DataFrame
    df = pd.DataFrame([{
        "date": t.date,
        "description": t.description,
        "type": t.type,
        "amount": t.amount,
        "category": t.category
    } for t in transactions])

    # Ensure data is sorted by date for timeline graphs
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values(by="date", inplace=True)

    # Generate Plotly figures
    fig_categories = px.pie(
        df[df["type"] == "Expense"],  # Only show expenses in pie chart
        values="amount",
        names="category",
        title="Expenses by Category",
        template="plotly_white"
    )
    
    fig_timeline = px.line(
        df,
        x="date",
        y="amount",
        color="type",
        title="Transaction Timeline",
        markers=True,
        template="plotly_white"
    )

    # Convert to standalone HTML components
    charts = {
        "category_dist": fig_categories.to_html(
            full_html=False, include_plotlyjs='cdn'
        ),
        "timeline": fig_timeline.to_html(
            full_html=False, include_plotlyjs='cdn'
        )
    }

    # Add to dashboard endpoint
    charts.update({
        "total_balance": df[df["type"] == "Income"]["amount"].sum() - 
                        df[df["type"] == "Expense"]["amount"].sum(),
        "monthly_summary": px.bar(
            df.groupby([pd.Grouper(key='date', freq='M'), 'type'])
            .sum()
            .reset_index(),
            x="date",
            y="amount",
            color="type",
            barmode="group",
            title="Monthly Summary"
        ).to_html(full_html=False)
    })

    db.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "charts": charts,
        "transactions": transactions
    })

# Add after the dashboard endpoint (around line 106)
@app.delete("/transaction/{transaction_id}")
async def delete_transaction(transaction_id: int):
    db = SessionLocal()
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    if not transaction:
        db.close()
        return {"error": "Transaction not found"}
    
    db.delete(transaction)
    db.commit()
    db.close()
    return {"message": f"Deleted transaction {transaction_id}"}