"""Tattelecom Intercom custom integration."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up entry configured via user interface."""

    is_new: bool = get_config_value(entry, OPTION_IS_FROM_FLOW, False)

    if is_new:
        hass.config_entries.async_update_entry(entry, data=entry.data, options={})

    _updater: IntercomUpdater = IntercomUpdater(
        hass,
        get_config_value(entry, CONF_PHONE),
        get_config_value(entry, CONF_TOKEN),
        get_config_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        get_config_value(entry, CONF_TIMEOUT, DEFAULT_TIMEOUT),
    )

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {UPDATER: _updater}

    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = entry.add_update_listener(
        async_update_options
    )

    async def async_start(with_sleep: bool = False) -> None:
        """Async start."""

        if entry.state == ConfigEntryState.SETUP_IN_PROGRESS:
            await _updater.async_config_entry_first_refresh()
        else:
            await _updater.async_update()  # Используем новый метод

        if with_sleep:
            await asyncio.sleep(DEFAULT_SLEEP)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if is_new:
        await async_start()
        await asyncio.sleep(DEFAULT_SLEEP)
    else:
        hass.loop.call_later(
            DEFAULT_CALL_DELAY,
            lambda: hass.async_create_task(async_start(True)),
        )

    async def async_stop(event: Event) -> None:
        """Async stop"""

        await _updater.async_stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_stop)

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for entry that was configured via user interface.

    :param hass: Home Assistant: Home Assistant object
    :param entry: Config Entry: Config Entry object
    """
    if entry.entry_id not in hass.data[DOMAIN]:
        return

    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove entry configured via user interface.

    :param hass: Home Assistant: Home Assistant object
    :param entry: Config Entry: Config Entry object
    :return bool: Is success
    """
    if is_unload := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        _updater: IntercomUpdater = hass.data[DOMAIN][entry.entry_id][UPDATER]
        await _updater.async_stop()

        _update_listener: CALLBACK_TYPE = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        _update_listener()

        hass.data[DOMAIN].pop(entry.entry_id)

    return is_unload
