"""Structured SQL retrieval for prices, availability, sizes, agents."""

from __future__ import annotations

from typing import Any

from .db import fetch_all, fetch_one


def get_property(property_id: str) -> dict | None:
    return fetch_one(
        """
        SELECT p.*, d.name AS developer_name, d.trust_notes,
               a.name AS agent_name, a.phone AS agent_phone, a.desk AS agent_desk,
               pp.name AS payment_plan_name, pp.summary AS payment_plan_summary
        FROM properties p
        LEFT JOIN developers d ON p.developer_id = d.developer_id
        LEFT JOIN agents a ON p.agent_id = a.agent_id
        LEFT JOIN payment_plans pp ON p.payment_plan_id = pp.payment_plan_id
        WHERE p.property_id = ?
        """,
        (property_id,),
    )


def search_properties(
    *,
    city: str | None = None,
    area: str | None = None,
    purpose: str | None = None,
    bedrooms: int | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    property_type: str | None = None,
    available_only: bool = True,
    limit: int = 10,
) -> list[dict]:
    clauses = ["1=1"]
    params: list[Any] = []
    if available_only:
        clauses.append("status = 'available'")
    if city:
        clauses.append("LOWER(city) = LOWER(?)")
        params.append(city)
    if area:
        clauses.append("LOWER(area) LIKE LOWER(?)")
        params.append(f"%{area}%")
    if purpose:
        clauses.append("LOWER(purpose) = LOWER(?)")
        params.append(purpose)
    if bedrooms is not None:
        clauses.append("bedrooms = ?")
        params.append(bedrooms)
    if property_type:
        clauses.append("LOWER(property_type) = LOWER(?)")
        params.append(property_type)
    if max_price is not None:
        clauses.append("price_pkr <= ?")
        params.append(max_price)
    if min_price is not None:
        clauses.append("price_pkr >= ?")
        params.append(min_price)
    sql = f"""
        SELECT property_id, title, city, area, purpose, property_type,
               bedrooms, size_value, size_unit, price_pkr, price_display,
               status, amenities, schools_nearby, hospitals_nearby,
               agent_id, developer_id, payment_plan_id, investment_tag
        FROM properties
        WHERE {' AND '.join(clauses)}
        ORDER BY price_pkr ASC
        LIMIT ?
    """
    params.append(limit)
    return fetch_all(sql, tuple(params))


def get_agent(agent_id: str) -> dict | None:
    return fetch_one("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))


def get_developer(developer_id: str) -> dict | None:
    return fetch_one("SELECT * FROM developers WHERE developer_id = ?", (developer_id,))


def get_payment_plan(plan_id: str) -> dict | None:
    return fetch_one(
        "SELECT * FROM payment_plans WHERE payment_plan_id = ?", (plan_id,)
    )


def price_for(property_id: str) -> dict | None:
    return fetch_one(
        "SELECT property_id, title, price_pkr, price_display, status FROM properties WHERE property_id = ?",
        (property_id,),
    )


def availability(property_id: str) -> dict | None:
    return fetch_one(
        "SELECT property_id, title, status FROM properties WHERE property_id = ?",
        (property_id,),
    )
