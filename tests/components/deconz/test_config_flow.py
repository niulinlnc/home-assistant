"""Tests for deCONZ config flow."""
from unittest.mock import patch

import asyncio

from homeassistant.components.deconz import config_flow
from tests.common import MockConfigEntry

import pydeconz


async def test_flow_works(hass, aioclient_mock):
    """Test that config flow works."""
    aioclient_mock.get(pydeconz.utils.URL_DISCOVER, json=[
        {'id': 'id', 'internalipaddress': '1.2.3.4', 'internalport': 80}
    ], headers={'content-type': 'application/json'})
    aioclient_mock.post('http://1.2.3.4:80/api', json=[
        {"success": {"username": "1234567890ABCDEF"}}
    ], headers={'content-type': 'application/json'})

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    await flow.async_step_user()
    result = await flow.async_step_link(user_input={})

    assert result['type'] == 'create_entry'
    assert result['title'] == 'deCONZ-id'
    assert result['data'] == {
        'bridgeid': 'id',
        'host': '1.2.3.4',
        'port': 80,
        'api_key': '1234567890ABCDEF'
    }


async def test_flow_bridge_discovery_fails(hass, aioclient_mock):
    """Test config flow works when discovery fails."""
    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    with patch('pydeconz.utils.async_discovery',
               side_effect=asyncio.TimeoutError):
        result = await flow.async_step_user()

    assert result['type'] == 'form'
    assert result['step_id'] == 'init'


async def test_flow_no_discovered_bridges(hass, aioclient_mock):
    """Test config flow discovers no bridges."""
    aioclient_mock.get(pydeconz.utils.URL_DISCOVER, json=[],
                       headers={'content-type': 'application/json'})

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result['type'] == 'form'
    assert result['step_id'] == 'init'


async def test_flow_one_bridge_discovered(hass, aioclient_mock):
    """Test config flow discovers one bridge."""
    aioclient_mock.get(pydeconz.utils.URL_DISCOVER, json=[
        {'id': 'id', 'internalipaddress': '1.2.3.4', 'internalport': 80}
    ], headers={'content-type': 'application/json'})

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result['type'] == 'form'
    assert result['step_id'] == 'link'
    assert flow.deconz_config['host'] == '1.2.3.4'


async def test_flow_two_bridges_discovered(hass, aioclient_mock):
    """Test config flow discovers two bridges."""
    aioclient_mock.get(pydeconz.utils.URL_DISCOVER, json=[
        {'id': 'id1', 'internalipaddress': '1.2.3.4', 'internalport': 80},
        {'id': 'id2', 'internalipaddress': '5.6.7.8', 'internalport': 80}
    ], headers={'content-type': 'application/json'})

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user()
    assert result['data_schema']({'host': '1.2.3.4'})
    assert result['data_schema']({'host': '5.6.7.8'})


async def test_flow_two_bridges_selection(hass, aioclient_mock):
    """Test config flow selection of one of two bridges."""
    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass
    flow.bridges = [
        {'bridgeid': 'id1', 'host': '1.2.3.4', 'port': 80},
        {'bridgeid': 'id2', 'host': '5.6.7.8', 'port': 80}
    ]

    result = await flow.async_step_user(user_input={'host': '1.2.3.4'})
    assert result['type'] == 'form'
    assert result['step_id'] == 'link'
    assert flow.deconz_config['host'] == '1.2.3.4'


async def test_flow_manual_configuration(hass, aioclient_mock):
    """Test config flow with manual input."""
    aioclient_mock.get(pydeconz.utils.URL_DISCOVER, json=[])

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    user_input = {'host': '1.2.3.4', 'port': 80}

    result = await flow.async_step_user(user_input)
    assert result['type'] == 'form'
    assert result['step_id'] == 'link'
    assert flow.deconz_config == user_input


async def test_link_no_api_key(hass):
    """Test config flow should abort if no API key was possible to retrieve."""
    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass
    flow.deconz_config = {'host': '1.2.3.4', 'port': 80}

    with patch('pydeconz.utils.async_get_api_key',
               side_effect=pydeconz.errors.ResponseError):
        result = await flow.async_step_link(user_input={})

    assert result['type'] == 'form'
    assert result['step_id'] == 'link'
    assert result['errors'] == {'base': 'no_key'}


async def test_bridge_discovery(hass):
    """Test a bridge being discovered."""
    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_discovery({
        'host': '1.2.3.4',
        'port': 80,
        'serial': 'id'
    })

    assert result['type'] == 'form'
    assert result['step_id'] == 'link'


async def test_bridge_discovery_already_configured(hass):
    """Test if a discovered bridge has already been configured."""
    MockConfigEntry(domain='deconz', data={
        'host': '1.2.3.4'
    }).add_to_hass(hass)

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_discovery({
        'host': '1.2.3.4',
        'port': 80,
        'serial': 'id'
    })

    assert result['type'] == 'abort'


async def test_import_without_api_key(hass):
    """Test importing a host without an API key."""
    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_import({
        'host': '1.2.3.4',
    })

    assert result['type'] == 'form'
    assert result['step_id'] == 'link'


async def test_import_with_api_key(hass):
    """Test importing a host with an API key."""
    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass

    result = await flow.async_step_import({
        'bridgeid': 'id',
        'host': '1.2.3.4',
        'port': 80,
        'api_key': '1234567890ABCDEF'
    })

    assert result['type'] == 'create_entry'
    assert result['title'] == 'deCONZ-id'
    assert result['data'] == {
        'bridgeid': 'id',
        'host': '1.2.3.4',
        'port': 80,
        'api_key': '1234567890ABCDEF'
    }


async def test_create_entry(hass, aioclient_mock):
    """Test that _create_entry work and that bridgeid can be requested."""
    aioclient_mock.get('http://1.2.3.4:80/api/1234567890ABCDEF/config',
                       json={"bridgeid": "id"},
                       headers={'content-type': 'application/json'})

    flow = config_flow.DeconzFlowHandler()
    flow.hass = hass
    flow.deconz_config = {'host': '1.2.3.4',
                          'port': 80,
                          'api_key': '1234567890ABCDEF'}

    result = await flow._create_entry()

    assert result['type'] == 'create_entry'
    assert result['title'] == 'deCONZ-id'
    assert result['data'] == {
        'bridgeid': 'id',
        'host': '1.2.3.4',
        'port': 80,
        'api_key': '1234567890ABCDEF'
    }


async def test_hassio_single_instance(hass):
    """Test we only allow a single config flow."""
    MockConfigEntry(domain='deconz', data={
        'host': '1.2.3.4'
    }).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        'deconz', context={'source': 'hassio'})
    assert result['type'] == 'abort'
    assert result['reason'] == 'one_instance_only'


async def test_hassio_confirm(hass):
    """Test we can finish a config flow."""
    result = await hass.config_entries.flow.async_init(
        'deconz',
        data={
            'addon': 'Mock Addon',
            'host': 'mock-deconz',
            'port': 80,
            'serial': 'id',
            'api_key': '1234567890ABCDEF',
        },
        context={'source': 'hassio'}
    )
    assert result['type'] == 'form'
    assert result['step_id'] == 'hassio_confirm'
    assert result['description_placeholders'] == {
        'addon': 'Mock Addon',
    }

    result = await hass.config_entries.flow.async_configure(
        result['flow_id'], user_input={}
    )

    assert result['type'] == 'create_entry'
    assert result['result'].data == {
        'host': 'mock-deconz',
        'port': 80,
        'bridgeid': 'id',
        'api_key': '1234567890ABCDEF'
    }
