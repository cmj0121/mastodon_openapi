from __future__ import annotations

from pydantic import BaseModel


class Contact(BaseModel):
    """
    Contact information for the exposed API.

    ref: https://swagger.io/specification/#contact-object
    """

    name: str | None = None
    url: str | None = None
    email: str | None = None


class License(BaseModel):
    """
    License information for the exposed API.

    ref: https://swagger.io/specification/#license-object
    """

    name: str
    url: str | None = None
    identifier: str | None = None


class Info(BaseModel):
    """
    The object provides metadata about the API

    ref: https://swagger.io/specification/#info-object
    """

    title: str
    version: str
    summary: str | None = None
    description: str | None = None
    termsOfService: str | None = None
    contact: Contact | None = None
    license: License | None = None
