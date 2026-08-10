import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember
from app.schemas.assistant import ChatRequest, ChatResponse
from app.api.routes.dashboard import get_summary

# Attempt to import google-genai
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False

router = APIRouter()


def build_offline_response(summary, user_msg: str) -> str:
    msg = user_msg.lower().strip()

    if "inactive customer" in msg or "inactive customers" in msg:
        body = (
            f"👥 **Customer Status Breakdown**\n"
            f"• Total Customers: {summary.total_customers}\n"
            f"• Active Customers: {summary.active_customers}\n"
            f"• Inactive Customers: {summary.inactive_customers}\n\n"
            f"You currently have {summary.inactive_customers} inactive customer(s). "
            f"You can view and reactivate them under the Customers screen."
        )
    elif "active customer" in msg or "active customers" in msg:
        body = (
            f"👥 **Customer Status Breakdown**\n"
            f"• Total Customers: {summary.total_customers}\n"
            f"• Active Customers: {summary.active_customers}\n"
            f"• Inactive Customers: {summary.inactive_customers}\n\n"
            f"You currently have {summary.active_customers} active customer(s) generating business."
        )
    elif "customer" in msg:
        body = (
            f"👥 **Customer Overview**\n"
            f"• Total Customers: {summary.total_customers}\n"
            f"• Active Customers: {summary.active_customers}\n"
            f"• Inactive Customers: {summary.inactive_customers}"
        )
    elif "inactive product" in msg or "inactive products" in msg:
        body = (
            f"📦 **Product Status Breakdown**\n"
            f"• Total Products: {summary.total_products}\n"
            f"• Active Products: {summary.active_products}\n"
            f"• Inactive Products: {summary.inactive_products}\n\n"
            f"You currently have {summary.inactive_products} inactive product(s). "
            f"You can reactivate them under the Products screen."
        )
    elif "active product" in msg or "active products" in msg or ("active" in msg and "product" in msg):
        body = (
            f"📦 **Product Status Breakdown**\n"
            f"• Total Products: {summary.total_products}\n"
            f"• Active Products: {summary.active_products}\n"
            f"• Inactive Products: {summary.inactive_products}\n\n"
            f"You currently have {summary.active_products} active product(s) in your catalog."
        )
    elif "low stock" in msg:
        if summary.low_stock_products == 0:
            body = "⚠️ **Stock Status**: All products are currently above minimum stock levels."
        else:
            body = (
                f"⚠️ **Low Stock Alert**\n"
                f"• Low Stock Products: {summary.low_stock_products}\n"
                f"• Out of Stock Products: {summary.out_of_stock_products}\n\n"
                f"Please restock these items soon under the Products & Inventory screen."
            )
    elif "product" in msg or "inventory" in msg or "stock" in msg:
        body = (
            f"📦 **Inventory Summary**\n"
            f"• Total Products: {summary.total_products}\n"
            f"• Active Products: {summary.active_products}\n"
            f"• Inactive Products: {summary.inactive_products}\n"
            f"• Low Stock Items: {summary.low_stock_products}\n"
            f"• Out of Stock Items: {summary.out_of_stock_products}"
        )
    elif "pending" in msg or "unpaid" in msg:
        body = (
            f"📄 **Pending Invoices Overview**\n"
            f"• Pending/Unpaid Invoices: {summary.unpaid_invoices}\n"
            f"• Partially Paid Invoices: {summary.partially_paid_invoices}\n"
            f"• Paid Invoices: {summary.paid_invoices}\n"
            f"• Total Invoices: {summary.total_invoices}\n"
            f"• Outstanding Balance: ₹{summary.outstanding_balance:.2f}\n\n"
            f"You have {summary.unpaid_invoices} pending invoice(s) with an outstanding balance of ₹{summary.outstanding_balance:.2f}."
        )
    elif "invoice" in msg:
        body = (
            f"📄 **Invoice Overview**\n"
            f"• Total Invoices: {summary.total_invoices}\n"
            f"• Paid Invoices: {summary.paid_invoices}\n"
            f"• Pending/Unpaid Invoices: {summary.unpaid_invoices}\n"
            f"• Partially Paid Invoices: {summary.partially_paid_invoices}\n"
            f"• Outstanding Balance: ₹{summary.outstanding_balance:.2f}"
        )
    elif "payment" in msg or "revenue" in msg or "sales" in msg:
        body = (
            f"💰 **Revenue & Payment Summary**\n"
            f"• Today's Revenue: ₹{summary.today_revenue:.2f}\n"
            f"• Monthly Revenue: ₹{summary.monthly_revenue:.2f}\n"
            f"• Total Payments Recorded: {summary.total_payments}\n"
            f"• Outstanding Balance: ₹{summary.outstanding_balance:.2f}"
        )
    elif "outstanding" in msg or "balance" in msg:
        body = (
            f"💳 **Outstanding Balance**\n"
            f"• Current Outstanding Balance: ₹{summary.outstanding_balance:.2f}\n"
            f"• Pending/Unpaid Invoices: {summary.unpaid_invoices}\n"
            f"• Partially Paid Invoices: {summary.partially_paid_invoices}"
        )
    elif "today" in msg or "overview" in msg:
        body = (
            f"📊 **Today's Business Overview**\n"
            f"• Today's Revenue: ₹{summary.today_revenue:.2f}\n"
            f"• Monthly Revenue: ₹{summary.monthly_revenue:.2f}\n"
            f"• Active Customers: {summary.active_customers}\n"
            f"• Active Products: {summary.active_products}\n"
            f"• Pending Invoices: {summary.unpaid_invoices}"
        )
    elif "insight" in msg or "recommendation" in msg or "suggestion" in msg or "improvin" in msg or "summary" in msg:
        body = (
            f"📈 **Business Insights & Recommendations**\n\n"
            f"1. **Revenue**: Monthly revenue is ₹{summary.monthly_revenue:.2f} (₹{summary.today_revenue:.2f} earned today).\n"
            f"2. **Receivables**: Outstanding balance is ₹{summary.outstanding_balance:.2f} across {summary.unpaid_invoices} pending invoice(s).\n"
            f"3. **Inventory**: {summary.low_stock_products} product(s) require stock adjustment.\n"
            f"4. **Customers**: {summary.active_customers} active out of {summary.total_customers} total customers.\n\n"
            f"💡 **Suggestions for Improving Business**: Follow up on pending invoices to accelerate cash flow, re-engage inactive customers, and restock low items."
        )
    else:
        body = (
            f"Hello! I am your Mercura Business Assistant. How can I help you today?\n\n"
            f"You can ask me about:\n"
            f"• *How many customers do I have?*\n"
            f"• *Show active / inactive customers*\n"
            f"• *How many products are active? / Inventory summary*\n"
            f"• *Low stock products*\n"
            f"• *Which invoices are pending?*\n"
            f"• *How much outstanding balance do I have?*\n"
            f"• *What is today's business summary?*\n"
            f"• *Give me business insights / suggestions*"
        )

    return f"🤖 **Mercura Business Assistant**\n\n{body}"


@router.post("/chat", response_model=ChatResponse)
def chat_with_assistant(
    business_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    user_msg = ""
    if request.messages:
        user_msg = request.messages[-1].content.strip()

    # Always fetch live summary data for context or offline fallback
    try:
        summary = get_summary(business_id=business_id, db=db, membership=membership)
    except Exception:
        summary = None

    api_key = os.getenv("GEMINI_API_KEY")

    if not HAS_GENAI or not api_key:
        if summary:
            return ChatResponse(response=build_offline_response(summary, user_msg))
        return ChatResponse(
            response="🤖 **Mercura Business Assistant**\n\nWelcome! I am ready to assist with your business operations."
        )

    # Use Gemini API if available
    try:
        context_data = summary.model_dump_json(indent=2) if summary else "{}"
        system_instruction = (
            "You are the Mercura AI Business Assistant. You help small business owners analyze their operations, "
            "understand sales data, and manage inventory. Be concise, professional, and helpful. "
            f"Real-time business summary:\n{context_data}\n"
        )
        client = genai.Client(api_key=api_key)
        contents = []
        for msg in request.messages:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            ),
        )
        return ChatResponse(response=response.text or "I could not generate a response.")
    except Exception:
        # Fallback cleanly to Offline Assistant on any error
        if summary:
            return ChatResponse(response=build_offline_response(summary, user_msg))
        return ChatResponse(
            response="🤖 **Mercura Business Assistant**\n\nWelcome! I am ready to assist with your business operations."
        )
