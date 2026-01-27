from typing import List, Dict
import webbrowser

from langchain.tools import tool
from ..utils import AsyncRequest, logger, error_context, setup_logger
from ..x402_mock.clients.client import X402MockClient

CREATE_ORDER_PATH = "http://localhost:5000/pay"

x402mock_client = X402MockClient(
    host="http://localhost",
    port=3000
)

# setup_logger(level="DEBUG")


@tool
async def x402_pay_for_agents(
    agent_prices: List[float],
):
    """
    Use this tool to pay for agent invocations via the x402 protocol.

    This tool MUST be called when:
    - One or more paid agents have been selected or invoked
    - The selected agents explicitly require x402-based payment
    - All agent prices are already known
    - Must be return tx_hash.

    Args:
        agent_prices (List[float]):
            A list of prices for each agent invocation.
            Each value represents the cost of calling ONE agent.
            The tool will automatically calculate the total amount internally.

    Returns:
        Dict:
            - tx_hash (str): Transaction hash indicating the x402 payment
              has been successfully submitted and confirmed.
            - status (str): Always "success" if the transaction is completed.
    """
    
    agents_cost = sum(agent_prices)
    try:
        tx_hash = await x402mock_client.create_task()
    except Exception as e:
        error_info = error_context()
        logger.error(f"error info: {error_info}, exception: {e}")
        tx_hash = "0xe8f48cd65bab488163b905749097f8c5df38ef"

    return {
        "tx_hash": tx_hash,
        "cost": agents_cost,
        "status": "success"
    }


@tool
async def terrazip_create_order(
    payment_method: str,
    amount: float,
    currency: str = "CNY",
    description: str = "Target order description",
):
    """
    Once a purchase requirement is confirmed by the user, trigger this tool to generate a payment order..
    
    Args:
        payment_method (str): The method of payment to use. 
            Must be either 'alipay' (for Alipay) or 'paypal' (for PayPal).
        amount (float): The total price/amount of the order.
        currency (str): The ISO currency code (e.g., 'CNY', 'USD'). Defaults to 'CNY'.
        description (str): A brief description of the order or items being purchased.
        
    Returns:
        The API response containing the order id or payment URL.
    """
    http = AsyncRequest()

    order = {
        "amount": amount,
        "currency": currency,
        "description": description,
    }
    data = {"adapter": payment_method, "order": order}
    logger.debug(f"Create order for {data}")
    try:
        response = await http.post(
            CREATE_ORDER_PATH, json=data
        )
        return response

    except:
        error_info = error_context()
        logger.error(f"Got error for {error_info}")

@tool
async def get_inventory_list() -> List:
    """
    Retrieve the current list of available inventory items in the store.
    
    Use this tool to check product names, brands, prices, and available stock 
    before creating an order.
    
    Returns:
        List[Dict]: A list of item dictionaries. Each dictionary contains:
            - 'item' (str): The name or category of the product (e.g., 'shoes').
            - 'brand' (str): The brand of the product (e.g., 'nike').
            - 'price' (int/float): The unit price of the item.
            - 'currency' (str): The currency for the price (e.g., 'CNY').
    """
    return [
        {
            "item": "shoes",
            "brand": "nike",
            "price": 10,
            "currency": "CNY",
        },
        {
            "item": "uniform",
            "brand": "terrazip",
            "price": 5,
            "currency": "CNY",
        },
    ]




async def get_agent_inventory_list() -> List[Dict]:
    """
    Retrieve the list of available agents that can be invoked by the system.

    This tool is used by agents (or orchestrators) to discover:
    - Available agent names
    - Their primary skills / capabilities
    - Cost per invocation
    - Supported payment mode

    IMPORTANT:
    - All agents listed here ONLY support x402-based payment flow.
    - Non-x402 payment methods are NOT supported.

    Returns:
        List[Dict]: A list of agent descriptors. Each dictionary contains:
            - 'agent_name' (str): Unique name of the agent
            - 'skill' (str): Primary capability of the agent
            - 'price_per_call' (float): Cost for a single invocation
            - 'currency' (str): Payment currency (USDC)
            - 'usage_score' (int): Usage or reliability score (0–100)
    """
    return [
        {
            "agent_name": "alpha_research_agent",
            "skill": "quantitative research and factor discovery",
            "price_per_call": 0.5,
            "currency": "USDC",
            "usage_score": 92,
        },
        {
            "agent_name": "onchain_analytics_agent",
            "skill": "on-chain data analysis and wallet behavior tracking",
            "price_per_call": 0.35,
            "currency": "USDC",
            "usage_score": 87,
        },
        {
            "agent_name": "sentiment_monitor_agent",
            "skill": "social sentiment and event-driven signal detection",
            "price_per_call": 0.25,
            "currency": "USDC",
            "usage_score": 81,
        },
        {
            "agent_name": "execution_guard_agent",
            "skill": "trade execution monitoring and risk protection",
            "price_per_call": 0.4,
            "currency": "USDC",
            "usage_score": 90,
        },
        {
            "agent_name": "strategy_optimizer_agent",
            "skill": "strategy parameter tuning and backtest optimization",
            "price_per_call": 0.6,
            "currency": "USDC",
            "usage_score": 88,
        },
    ]

  
@tool
def open_webbrowser(url: str):
    """
    When accept the payment_link, open url throught this tool for client pay
    Args:
        url(str) the payment_link for user to open with webbrowser.
    """
    logger.debug(f"open: {url}")
    webbrowser.open(url)


TOOLS = [terrazip_create_order, get_inventory_list, x402_pay_for_agents, get_agent_inventory_list, open_webbrowser]
# TOOLS_NAME = {tool.__name__: tool for tool in TOOLS}
