"""Unified Airline and Retail entry points for the final-candidate edition."""

from .airline import register_domain as register_airline_domain
from .retail import register_domain as register_retail_domain


def register_domains() -> None:
    register_airline_domain()
    register_retail_domain()


__all__ = ["register_domains", "register_airline_domain", "register_retail_domain"]
