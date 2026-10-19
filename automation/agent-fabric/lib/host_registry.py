"""Strict registry for the Agent Fabric hosts."""
from __future__ import annotations

import json
import re
from pathlib import Path


_NAME = re.compile(r'^[a-z0-9-]+$')
_TOP_LEVEL = {'version', 'hub', 'share', 'hosts'}
_SHARE = {'host', 'name', 'user'}
_HOST = {'hostname_prefix', 'role', 'ssh_alias', 'catalog_root', 'repo', 'path', 'gui_cwd', 'runtimes'}


class RegistryError(ValueError):
    """The host registry is absent, malformed, or unsafe."""


def _absolute(value):
    return isinstance(value, str) and Path(value).is_absolute()


def _name(value):
    return isinstance(value, str) and bool(_NAME.fullmatch(value))


class HostRegistry:
    """Load and validate the shared, versioned host registry."""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).resolve().parents[3] / 'config' / 'hosts.json'
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, TypeError, json.JSONDecodeError) as error:
            raise RegistryError('INVALID_HOST_REGISTRY') from error
        self._hosts, self.hub, self.share = self._validate(value)

    @staticmethod
    def _validate(value):
        if not isinstance(value, dict) or set(value) != _TOP_LEVEL or value.get('version') != 1:
            raise RegistryError('INVALID_HOST_REGISTRY')
        share = value['share']
        hosts = value['hosts']
        if not isinstance(share, dict) or set(share) != _SHARE or any(not isinstance(share[key], str) or not share[key] for key in _SHARE) or not _name(share['name']):
            raise RegistryError('INVALID_HOST_REGISTRY')
        if not isinstance(hosts, dict) or not hosts or any(not _name(name) for name in hosts):
            raise RegistryError('INVALID_HOST_REGISTRY')
        if not _name(value['hub']) or value['hub'] not in hosts:
            raise RegistryError('INVALID_HOST_REGISTRY')
        result = {}
        prefixes = []
        hubs = []
        for name, host in hosts.items():
            if not isinstance(host, dict) or set(host) != _HOST:
                raise RegistryError('INVALID_HOST_REGISTRY')
            if not isinstance(host['hostname_prefix'], str) or not host['hostname_prefix']:
                raise RegistryError('INVALID_HOST_REGISTRY')
            if host['role'] not in ('hub', 'spoke') or not _name(host['ssh_alias']):
                raise RegistryError('INVALID_HOST_REGISTRY')
            if not all(_absolute(host[key]) for key in ('catalog_root', 'repo', 'gui_cwd')):
                raise RegistryError('INVALID_HOST_REGISTRY')
            if not isinstance(host['path'], str) or not host['path']:
                raise RegistryError('INVALID_HOST_REGISTRY')
            runtimes = host['runtimes']
            if not isinstance(runtimes, list) or not runtimes or any(not isinstance(runtime, str) or not runtime for runtime in runtimes) or len(runtimes) != len(set(runtimes)) or 'pi' not in runtimes:
                raise RegistryError('INVALID_HOST_REGISTRY')
            prefixes.append(host['hostname_prefix'])
            if host['role'] == 'hub':
                hubs.append(name)
            result[name] = dict(host, name=name)
        if hubs != [value['hub']]:
            raise RegistryError('INVALID_HOST_REGISTRY')
        for index, prefix in enumerate(prefixes):
            if any(prefix != other and (prefix.startswith(other) or other.startswith(prefix)) for other in prefixes[index + 1:]):
                raise RegistryError('INVALID_HOST_REGISTRY')
        return result, value['hub'], dict(share)

    @property
    def hosts(self):
        return dict(self._hosts)

    def get(self, name):
        try:
            return self._hosts[name]
        except (KeyError, TypeError) as error:
            raise KeyError(name) from error

    def self_host(self, nodename):
        if not isinstance(nodename, str):
            return None
        for host in self._hosts.values():
            if nodename.startswith(host['hostname_prefix']):
                return host
        return None
