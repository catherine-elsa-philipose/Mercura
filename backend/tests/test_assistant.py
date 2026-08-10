import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
try:
    from google import genai
except ImportError:
    genai = None

from app.api.routes.assistant import chat_with_assistant
from app.schemas.assistant import ChatRequest, ChatMessage, ChatResponse
from app.schemas.dashboard import DashboardSummaryResponse

class TestAssistantRouter:
    @patch("app.api.routes.assistant.get_summary")
    def test_chat_without_genai_library(self, mock_get_summary):
        mock_summary = DashboardSummaryResponse(
            total_customers=10,
            active_customers=8,
            inactive_customers=2,
            total_products=100,
            active_products=95,
            inactive_products=5,
            low_stock_products=3,
            out_of_stock_products=1,
            total_invoices=20,
            paid_invoices=15,
            unpaid_invoices=3,
            partially_paid_invoices=2,
            cancelled_invoices=0,
            total_payments=15,
            today_revenue=Decimal("150.00"),
            monthly_revenue=Decimal("3000.00"),
            outstanding_balance=Decimal("200.00"),
        )
        mock_get_summary.return_value = mock_summary

        with patch("app.api.routes.assistant.HAS_GENAI", False):
            request = ChatRequest(messages=[ChatMessage(role="user", content="How many customers do I have?")])
            mock_db = MagicMock()
            mock_membership = MagicMock()

            response = chat_with_assistant(
                business_id=1,
                request=request,
                db=mock_db,
                membership=mock_membership
            )

            assert isinstance(response, ChatResponse)
            assert "Mercura Business Assistant" in response.response
            assert "Total Customers: 10" in response.response

    @patch("app.api.routes.assistant.get_summary")
    def test_chat_without_api_key(self, mock_get_summary):
        mock_summary = DashboardSummaryResponse(
            total_customers=10,
            active_customers=8,
            inactive_customers=2,
            total_products=100,
            active_products=95,
            inactive_products=5,
            low_stock_products=3,
            out_of_stock_products=1,
            total_invoices=20,
            paid_invoices=15,
            unpaid_invoices=3,
            partially_paid_invoices=2,
            cancelled_invoices=0,
            total_payments=15,
            today_revenue=Decimal("150.00"),
            monthly_revenue=Decimal("3000.00"),
            outstanding_balance=Decimal("200.00"),
        )
        mock_get_summary.return_value = mock_summary

        with patch("app.api.routes.assistant.HAS_GENAI", True), \
             patch("os.getenv", return_value=None):

            request = ChatRequest(messages=[ChatMessage(role="user", content="Show active customers")])
            mock_db = MagicMock()
            mock_membership = MagicMock()

            response = chat_with_assistant(
                business_id=1,
                request=request,
                db=mock_db,
                membership=mock_membership
            )

            assert isinstance(response, ChatResponse)
            assert "Mercura Business Assistant" in response.response
            assert "Active Customers: 8" in response.response

    @patch("app.api.routes.assistant.get_summary")
    def test_chat_success(self, mock_get_summary):
        mock_summary = DashboardSummaryResponse(
            total_customers=10,
            active_customers=8,
            inactive_customers=2,
            total_products=100,
            active_products=95,
            inactive_products=5,
            low_stock_products=3,
            out_of_stock_products=1,
            total_invoices=20,
            paid_invoices=15,
            unpaid_invoices=3,
            partially_paid_invoices=2,
            cancelled_invoices=0,
            total_payments=15,
            today_revenue=Decimal("150.00"),
            monthly_revenue=Decimal("3000.00"),
            outstanding_balance=Decimal("200.00"),
        )
        mock_get_summary.return_value = mock_summary

        mock_genai = MagicMock()
        mock_types = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello! I am your assistant."
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        mock_types.Content.side_effect = lambda role, parts: MagicMock(role=role, parts=parts)
        mock_types.Part.from_text.side_effect = lambda text: MagicMock(text=text)
        from types import SimpleNamespace
        mock_types.GenerateContentConfig.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)

        with patch("app.api.routes.assistant.HAS_GENAI", True), \
             patch("os.getenv", return_value="fake_api_key"), \
             patch("app.api.routes.assistant.genai", mock_genai), \
             patch("app.api.routes.assistant.types", mock_types):

            request = ChatRequest(messages=[ChatMessage(role="user", content="How is my business doing?")])
            mock_db = MagicMock()
            mock_membership = MagicMock()

            response = chat_with_assistant(
                business_id=1,
                request=request,
                db=mock_db,
                membership=mock_membership
            )

            mock_get_summary.assert_called_once_with(business_id=1, db=mock_db, membership=mock_membership)
            mock_genai.Client.assert_called_once_with(api_key="fake_api_key")

            mock_client.models.generate_content.assert_called_once()
            call_args = mock_client.models.generate_content.call_args[1]
            assert call_args["model"] == "gemini-2.5-flash"
            assert "How is my business doing?" in call_args["contents"][0].parts[0].text
            assert "150.00" in call_args["config"].system_instruction

            assert response.response == "Hello! I am your assistant."

    @patch("app.api.routes.assistant.get_summary")
    def test_chat_api_error_fallback(self, mock_get_summary):
        mock_summary = DashboardSummaryResponse(
            total_customers=10,
            active_customers=8,
            inactive_customers=2,
            total_products=100,
            active_products=95,
            inactive_products=5,
            low_stock_products=3,
            out_of_stock_products=1,
            total_invoices=20,
            paid_invoices=15,
            unpaid_invoices=3,
            partially_paid_invoices=2,
            cancelled_invoices=0,
            total_payments=15,
            today_revenue=Decimal("150.00"),
            monthly_revenue=Decimal("3000.00"),
            outstanding_balance=Decimal("200.00"),
        )
        mock_get_summary.return_value = mock_summary

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("API connection failed")

        with patch("app.api.routes.assistant.HAS_GENAI", True), \
             patch("os.getenv", return_value="fake_api_key"), \
             patch("app.api.routes.assistant.genai", mock_genai):

            request = ChatRequest(messages=[ChatMessage(role="user", content="Business summary")])
            mock_db = MagicMock()
            mock_membership = MagicMock()

            response = chat_with_assistant(
                business_id=1,
                request=request,
                db=mock_db,
                membership=mock_membership
            )

            assert "Mercura Business Assistant" in response.response
            assert "Business Insights & Recommendations" in response.response
