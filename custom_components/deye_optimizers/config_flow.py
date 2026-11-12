"""Config flow for Deye Cloud Optimizers."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import DeyeCloudAuthError, DeyeCloudClient, DeyeCloudError, hash_password
from .const import CONF_DATA_CENTER, CONF_PASSWORD_HASH, CONF_TOKEN, DATA_CENTERS, DEFAULT_DATA_CENTER, DOMAIN

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class DeyeOptimizersConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def _try_login(self, username: str, password_hash: str, data_center: str) -> tuple[dict | None, str | None]:
        token: dict[str, Any] = {}
        client = DeyeCloudClient(
            async_get_clientsession(self.hass), username, password_hash, data_center, on_token=token.update
        )
        try:
            await client.login()
            await client.stations()
        except DeyeCloudAuthError:
            return None, "invalid_auth"
        except DeyeCloudError as err:
            _LOGGER.debug("cannot connect: %s", err)
            return None, "cannot_connect"
        return token, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the deyecloud.com account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password_hash = hash_password(user_input[CONF_PASSWORD])
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()
            token, error = await self._try_login(username, password_hash, user_input[CONF_DATA_CENTER])
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD_HASH: password_hash,
                        CONF_DATA_CENTER: user_input[CONF_DATA_CENTER],
                        CONF_TOKEN: token,
                    },
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
                vol.Required(CONF_DATA_CENTER, default=DEFAULT_DATA_CENTER): SelectSelector(
                    SelectSelectorConfig(
                        options=DATA_CENTERS, mode=SelectSelectorMode.DROPDOWN, translation_key=CONF_DATA_CENTER
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for a new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            password_hash = hash_password(user_input[CONF_PASSWORD])
            token, error = await self._try_login(entry.data[CONF_USERNAME], password_hash, entry.data[CONF_DATA_CENTER])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD_HASH: password_hash, CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )
