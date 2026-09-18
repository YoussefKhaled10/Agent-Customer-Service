from src.routes.AdminKnowledgeRoutes import create_admin_knowledge_blueprint
from flask import Flask, jsonify

from src.helpers.config import settings
from src.routes import create_auth_blueprint
from src.routes.AdminAuthorizationRoutes import (
    create_admin_authorization_blueprint,
)
from src.routes.AdminCategoryRoutes import (
    create_admin_category_blueprint,
)
from src.routes.AdminConversationRoutes import (
    create_admin_conversation_blueprint,
)
from src.routes.AdminCustomerRoutes import (
    create_admin_customer_blueprint,
)
from src.routes.AdminInquiryRoutes import (
    create_admin_inquiry_blueprint,
)
from src.routes.AdminOrderRoutes import (
    create_admin_order_blueprint,
)
from src.routes.AdminPharmacistRequestRoutes import (
    create_admin_pharmacist_blueprint,
)
from src.routes.AdminProductRoutes import (
    create_admin_product_blueprint,
)
from src.routes.AdminToolExecutionRoutes import (
    create_admin_tool_execution_blueprint,
)
from src.routes.AgentRoutes import (
    create_agent_blueprint,
)
from src.routes.AuthUIRoutes import (
    create_auth_ui_blueprint,
)
from src.routes.ConversationRoutes import (
    create_conversation_blueprint,
)
from src.routes.RetrievalDebugRoutes import (
    create_retrieval_debug_blueprint,
)
from src.routes.ToolRoutes import (
    create_tools_blueprint,
)
from src.routes.UIRoutes import (
    create_ui_blueprint,
)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static",
        static_url_path="/static",
    )

    app.config["SECRET_KEY"] = settings.SECRET_KEY

    # Public authentication API.
    app.register_blueprint(
        create_auth_blueprint()
    )

    # Generic tool execution API.
    app.register_blueprint(
        create_tools_blueprint()
    )

    # LangGraph Agent API.
    app.register_blueprint(
        create_agent_blueprint()
    )

    # Public customer and admin UI pages.
    app.register_blueprint(
        create_ui_blueprint()
    )

    # Login and registration UI pages.
    app.register_blueprint(
        create_auth_ui_blueprint()
    )

    # Authenticated customer conversation history.
    app.register_blueprint(
        create_conversation_blueprint()
    )

    # Admin authorization and browser session.
    app.register_blueprint(
        create_admin_authorization_blueprint()
    )

    # Admin catalog management.
    app.register_blueprint(
        create_admin_category_blueprint()
    )

    app.register_blueprint(
        create_admin_product_blueprint()
    )

    # Admin customer and order management.
    app.register_blueprint(
        create_admin_customer_blueprint()
    )

    app.register_blueprint(
        create_admin_order_blueprint()
    )

    # Admin support management.
    app.register_blueprint(
        create_admin_inquiry_blueprint()
    )

    app.register_blueprint(
        create_admin_pharmacist_blueprint()
    )

    # Admin monitoring.
    app.register_blueprint(
        create_admin_conversation_blueprint()
    )

    app.register_blueprint(
        create_admin_tool_execution_blueprint()
    )

    app.register_blueprint(
        create_admin_knowledge_blueprint()
    )

    # Development-only raw retrieval inspection API.
    app.register_blueprint(
        create_retrieval_debug_blueprint()
    )

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        debug=settings.DEBUG,
        load_dotenv=False,
    )
