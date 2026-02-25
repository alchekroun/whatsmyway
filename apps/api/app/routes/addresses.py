from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.services.location_service import GeocodingError, ProviderConfigurationError, get_location_service

bp = Blueprint("addresses", __name__, url_prefix="/api/addresses")


@bp.get("/suggest")
def suggest_addresses() -> tuple[Response, int] | Response:
    query: str = str(request.args.get("q", "")).strip()
    if len(query) < 3:
        return jsonify({"suggestions": []})

    try:
        location_service = get_location_service()
        suggestions: list[str] = location_service.suggest_addresses(query, limit=5)
    except GeocodingError as exc:
        return jsonify({"error": str(exc)}), 502
    except ProviderConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        return jsonify({"error": "Upstream geocoding provider failure"}), 502

    return jsonify({"suggestions": suggestions})


@bp.post("/validate")
def validate_address() -> tuple[Response, int] | Response:
    payload_raw: Any = request.get_json(force=True)
    if not isinstance(payload_raw, dict):
        return jsonify({"error": "invalid JSON payload"}), 400

    address: str = str(payload_raw.get("address", "")).strip()
    if not address:
        return jsonify({"error": "address is required"}), 400

    try:
        location_service = get_location_service()
        _ = location_service.geocode_address(address)
        normalized: str = location_service.normalize_address(address)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GeocodingError as exc:
        return jsonify({"error": str(exc)}), 502
    except ProviderConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        return jsonify({"error": "Upstream geocoding provider failure"}), 502

    return jsonify({"valid": True, "normalized_address": normalized})
