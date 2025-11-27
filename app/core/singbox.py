from __future__ import annotations

import json
from copy import deepcopy
from pathlib import PosixPath
from typing import Any, Union

import commentjson

from app.core.abstract_core import AbstractCore
from app.core.types import BackendType, CoreType


class SingBoxConfig(AbstractCore):
    def __init__(
        self,
        config: Union[dict, str, PosixPath] = {},
        exclude_inbound_tags: set[str] | None = None,
        fallbacks_inbound_tags: set[str] | None = None,
    ) -> None:
        if isinstance(config, str):
            parsed_config = commentjson.loads(config)
        elif isinstance(config, (dict, PosixPath)):
            if isinstance(config, PosixPath):
                parsed_config = commentjson.loads(config.read_text(encoding="utf-8"))
            else:
                parsed_config = deepcopy(config)
        else:
            raise ValueError("Unsupported config type for Sing-Box core")

        super().__init__(parsed_config, exclude_inbound_tags or set(), fallbacks_inbound_tags or set())
        self._config = parsed_config
        self._validate()

        if fallbacks_inbound_tags:
            raise ValueError("Fallback inbound tags are not supported for Sing-Box cores")

        self._exclude_inbound_tags = exclude_inbound_tags or set()
        self._inbounds: list[str] = []
        self._inbounds_by_tag: dict[str, dict[str, Any]] = {}
        self._resolve_inbounds()

    def _validate(self) -> None:
        inbounds = self._config.get("inbounds")
        if not isinstance(inbounds, list) or not inbounds:
            raise ValueError("sing-box config doesn't have inbounds")

        for inbound in inbounds:
            if not isinstance(inbound, dict):
                raise ValueError("each inbound entry must be a JSON object")

            tag = inbound.get("tag")
            if not tag:
                raise ValueError("all inbounds must have a unique tag")
            if "," in tag:
                raise ValueError("character «,» is not allowed in inbound tag")
            if "<=>" in tag:
                raise ValueError("character «<=>» is not allowed in inbound tag")

            protocol = inbound.get("type") or inbound.get("protocol")
            if not protocol:
                raise ValueError(f"inbound '{tag}' must define a type/protocol")

    def _resolve_inbounds(self) -> None:
        for inbound in self._config.get("inbounds", []):
            tag = inbound.get("tag")
            if tag in self.exclude_inbound_tags:
                continue

            normalized = self._normalize_inbound(inbound)
            self._inbounds.append(tag)
            self._inbounds_by_tag[tag] = normalized

    def _normalize_inbound(self, inbound: dict[str, Any]) -> dict[str, Any]:
        protocol = str((inbound.get("type") or inbound.get("protocol") or "").lower())
        settings: dict[str, Any] = {
            "tag": inbound.get("tag", ""),
            "protocol": protocol,
            "network": "tcp",
            "port": self._extract_port(inbound),
            "tls": "none",
            "sni": [],
            "host": [],
            "path": "",
            "header_type": "",
            "fp": "",
            "alpn": [],
            "allowinsecure": False,
            "flow": inbound.get("flow", ""),
            "encryption": inbound.get("encryption", "none"),
            "method": inbound.get("method", ""),
            "password": inbound.get("password", ""),
            "is_2022": False,
            "pbk": "",
            "sid": "",
            "sids": [],
            "spx": "",
            "mldsa65Verify": inbound.get("tls", {}).get("mldsa65Verify"),
        }

        if isinstance(settings["method"], str) and settings["method"].startswith("2022-blake3"):
            settings["is_2022"] = True

        self._apply_tls_settings(settings, inbound.get("tls") or {})
        transport = inbound.get("transport") or {}
        if isinstance(transport, dict):
            self._apply_transport_settings(settings, transport)

        return settings

    def _extract_port(self, inbound: dict[str, Any]) -> Any:
        port = inbound.get("listen_port") or inbound.get("port")
        if isinstance(port, int):
            return port
        if isinstance(port, str) and port.strip():
            stripped = port.strip()
            return int(stripped) if stripped.isdigit() else stripped

        port_range = inbound.get("listen_port_range")
        if isinstance(port_range, dict):
            start = port_range.get("start") or port_range.get("from")
            end = port_range.get("end") or port_range.get("to")
            if start and end:
                return f"{start}-{end}"
            if start:
                return start
        elif isinstance(port_range, str):
            return port_range

        return None

    def _apply_tls_settings(self, settings: dict[str, Any], tls_config: dict[str, Any]) -> None:
        if not isinstance(tls_config, dict) or not tls_config.get("enabled"):
            return

        reality_cfg = tls_config.get("reality") or {}
        if isinstance(reality_cfg, dict) and reality_cfg.get("enabled"):
            settings["tls"] = "reality"
            settings["sni"] = self._ensure_list(tls_config.get("server_name")) or self._ensure_list(
                reality_cfg.get("handshake", {}).get("server")
            )
            settings["pbk"] = reality_cfg.get("public_key", "")
            sids = self._ensure_list(reality_cfg.get("short_id") or reality_cfg.get("short_ids"))
            settings["sids"] = sids
            settings["sid"] = sids[0] if sids else ""
            settings["spx"] = reality_cfg.get("spider_x") or reality_cfg.get("spider_x_content") or ""
            settings["mldsa65Verify"] = reality_cfg.get("mldsa65Verify") or reality_cfg.get("mldsa_65_verify")
            return

        settings["tls"] = "tls"
        settings["sni"] = self._ensure_list(tls_config.get("server_name")) or self._ensure_list(
            tls_config.get("server_name_list")
        )
        settings["alpn"] = self._ensure_list(tls_config.get("alpn"))
        settings["fp"] = tls_config.get("fingerprint", "")
        settings["allowinsecure"] = bool(tls_config.get("insecure"))

    def _apply_transport_settings(self, settings: dict[str, Any], transport: dict[str, Any]) -> None:
        network = transport.get("type") or transport.get("network")
        if isinstance(network, str) and network:
            settings["network"] = network.lower()
        network = settings["network"]

        if network in {"ws", "websocket"}:
            settings["path"] = transport.get("path", "")
            host_value = transport.get("headers", {}).get("Host") or transport.get("host")
            settings["host"] = self._ensure_list(host_value)
        elif network == "grpc":
            settings["path"] = transport.get("service_name", "")
            authority = transport.get("authority")
            if authority:
                settings["host"] = [authority]
        elif network in {"http", "h2", "h3"}:
            settings["path"] = transport.get("path", "")
            settings["host"] = self._ensure_list(transport.get("host"))
        elif network in {"quic", "kcp"}:
            settings["header_type"] = transport.get("header", "")
            if network == "kcp":
                settings["path"] = transport.get("seed", "")
        elif network in {"splithttp", "xhttp"}:
            settings["path"] = transport.get("path", "")
            settings["host"] = self._ensure_list(transport.get("host"))
        else:  # tcp/raw fallback
            host_value = transport.get("headers", {}).get("Host")
            if host_value:
                settings["host"] = self._ensure_list(host_value)
            if "path" in transport:
                settings["path"] = transport.get("path", "")

    def _ensure_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if v not in (None, "")]
        return [str(value)] if value not in (None, "") else []

    def to_str(self, **json_kwargs) -> str:
        return json.dumps(self._config, **json_kwargs)

    @property
    def backend_type(self) -> BackendType:
        return BackendType.SING_BOX

    @property
    def core_type(self) -> CoreType:
        return CoreType.SING_BOX

    @property
    def exclude_inbound_tags(self) -> set[str]:
        return self._exclude_inbound_tags

    @property
    def inbounds_by_tag(self) -> dict:
        return self._inbounds_by_tag

    @property
    def inbounds(self) -> list[str]:
        return self._inbounds
