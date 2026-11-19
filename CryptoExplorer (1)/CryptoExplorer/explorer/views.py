import re
import requests
from django.shortcuts import render
from django.views.decorators.http import require_GET

COINGECKO_API = "https://api.coingecko.com/api/v3"
DEFILLAMA_API = "https://api.llama.fi"
HEADERS = {"User-Agent": "CryptoExplorer/1.1"}

# Public read-only JSON-RPC endpoints. Public providers may rate-limit requests.
NETWORKS = {
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "rpc": "https://ethereum-rpc.publicnode.com",
        "symbol": "ETH",
    },
    "bnb": {
        "name": "BNB Chain",
        "chain_id": 56,
        "rpc": "https://bsc-rpc.publicnode.com",
        "symbol": "BNB",
    },
    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "rpc": "https://polygon-bor-rpc.publicnode.com",
        "symbol": "POL",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": "https://arbitrum-one-rpc.publicnode.com",
        "symbol": "ETH",
    },
}

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


def rpc_call(network_key, method, params=None):
    """Call a public EVM JSON-RPC endpoint. No private keys are used."""
    network = NETWORKS[network_key]
    response = requests.post(
        network["rpc"],
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or [],
        },
        headers=HEADERS,
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise ValueError(payload["error"].get("message", "RPC error"))
    return payload.get("result")


def get_network_status(network_key):
    try:
        block_hex = rpc_call(network_key, "eth_blockNumber")
        return {
            "ok": True,
            "block_number": int(block_hex, 16),
            "chain_id": NETWORKS[network_key]["chain_id"],
        }
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return {"ok": False, "error": "RPC временно недоступен"}


def get_wallet_balance(network_key, address):
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError("Введите корректный EVM-адрес (0x + 40 шестнадцатеричных символов).")
    balance_hex = rpc_call(network_key, "eth_getBalance", [address, "latest"])
    balance = int(balance_hex, 16) / 10**18
    return f"{balance:.8f}"


def get_transaction(network_key, tx_hash):
    if not HASH_RE.fullmatch(tx_hash):
        raise ValueError("Хеш транзакции должен содержать 0x и 64 шестнадцатеричных символа.")
    tx = rpc_call(network_key, "eth_getTransactionByHash", [tx_hash])
    if tx is None:
        return None
    receipt = rpc_call(network_key, "eth_getTransactionReceipt", [tx_hash])
    return {
        "hash": tx.get("hash"),
        "from": tx.get("from"),
        "to": tx.get("to") or "Контракт / создание контракта",
        "value": f"{int(tx.get('value', '0x0'), 16) / 10**18:.8f}",
        "block": int(tx["blockNumber"], 16) if tx.get("blockNumber") else "Ожидает включения",
        "status": (
            "Успешно" if receipt and receipt.get("status") == "0x1"
            else "Ошибка" if receipt and receipt.get("status") == "0x0"
            else "Ожидает подтверждения"
        ),
    }


def get_block(network_key, block_number):
    if not block_number.isdigit():
        raise ValueError("Номер блока должен быть целым неотрицательным числом.")
    block = rpc_call(network_key, "eth_getBlockByNumber", [hex(int(block_number)), False])
    if block is None:
        return None
    return {
        "number": int(block["number"], 16),
        "hash": block.get("hash"),
        "timestamp": int(block["timestamp"], 16),
        "transactions": len(block.get("transactions", [])),
        "gas_used": int(block.get("gasUsed", "0x0"), 16),
    }


def api_get(url, params=None):
    response = requests.get(url, params=params, headers=HEADERS, timeout=12)
    response.raise_for_status()
    return response.json()


def get_coins(query):
    if not query:
        return []
    try:
        data = api_get(f"{COINGECKO_API}/search", {"query": query})
        return [{
            "name": coin.get("name"),
            "symbol": (coin.get("symbol") or "").upper(),
            "image": coin.get("thumb"),
            "rank": coin.get("market_cap_rank"),
        } for coin in data.get("coins", [])[:15]]
    except (requests.RequestException, ValueError):
        return []


def get_chains(query):
    if not query:
        return []
    try:
        chains = api_get(f"{DEFILLAMA_API}/v2/chains")
        matches = []
        for chain in chains:
            name = str(chain.get("name", ""))
            if query.casefold() in name.casefold():
                matches.append({
                    "name": name,
                    "tvl": chain.get("tvl") or 0,
                    "token": chain.get("tokenSymbol") or "—",
                })
        return matches[:20]
    except (requests.RequestException, ValueError, TypeError):
        return []


def get_market():
    try:
        return api_get(
            f"{COINGECKO_API}/coins/markets",
            {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 10,
                "page": 1,
                "sparkline": "false",
            },
        )
    except (requests.RequestException, ValueError):
        return []


@require_GET
def index(request):
    query = request.GET.get("q", "").strip()[:80]
    category = request.GET.get("type", "all")
    if category not in {"all", "coins", "chains"}:
        category = "all"

    coins = get_coins(query) if category in {"all", "coins"} else []
    chains = get_chains(query) if category in {"all", "chains"} else []

    selected_network = request.GET.get("network", "ethereum")
    if selected_network not in NETWORKS:
        selected_network = "ethereum"

    interaction = {
        "network": selected_network,
        "network_name": NETWORKS[selected_network]["name"],
        "symbol": NETWORKS[selected_network]["symbol"],
        "address": request.GET.get("address", "").strip(),
        "tx_hash": request.GET.get("tx_hash", "").strip(),
        "block_number": request.GET.get("block_number", "").strip(),
    }
    interaction["status"] = get_network_status(selected_network)

    # Process only the requested operation, keeping requests predictable.
    if interaction["address"]:
        try:
            interaction["balance"] = get_wallet_balance(
                selected_network, interaction["address"]
            )
        except (requests.RequestException, ValueError) as exc:
            interaction["error"] = str(exc) if isinstance(exc, ValueError) else "Не удалось получить баланс через RPC."
    elif interaction["tx_hash"]:
        try:
            interaction["transaction"] = get_transaction(
                selected_network, interaction["tx_hash"]
            )
            if interaction["transaction"] is None:
                interaction["error"] = "Транзакция не найдена в выбранной сети."
        except (requests.RequestException, ValueError) as exc:
            interaction["error"] = str(exc) if isinstance(exc, ValueError) else "Не удалось получить транзакцию через RPC."
    elif interaction["block_number"]:
        try:
            interaction["block"] = get_block(
                selected_network, interaction["block_number"]
            )
            if interaction["block"] is None:
                interaction["error"] = "Блок не найден в выбранной сети."
        except (requests.RequestException, ValueError) as exc:
            interaction["error"] = str(exc) if isinstance(exc, ValueError) else "Не удалось получить блок через RPC."

    return render(request, "explorer/index.html", {
        "query": query,
        "category": category,
        "coins": coins,
        "chains": chains,
        "market": get_market(),
        "networks": NETWORKS,
        "interaction": interaction,
    })
