"""Fail-closed validation for declarative, non-applying fabric plans."""
import re
from pathlib import PurePosixPath
from urllib.parse import urlparse

CREDENTIAL_WORDS = ("password", "secret", "token", "private_key", "keychain")
AREA_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
EXPECTED = {"schema_version", "macbook", "mac_mini", "workspace_areas", "skills"}
NESTED = {"macbook": {"ssh_host_alias", "workspace_share_root", "future_share_name", "lock_root"}, "mac_mini": {"ssh_host_alias", "future_mount_target", "execution_identity"}, "skills": {"transport", "repository_url", "local_clone_roots"}, "local_clone_roots": {"macbook", "mac_mini"}, "area": {"id", "relative_path"}}


def _diagnostic(code, field, category, message):
    return {"code": code, "field": field, "category": category, "message": message}


def _credential_key(key):
    normalized = key.lower().replace("-", "_")
    return any(word in normalized for word in CREDENTIAL_WORDS)


def _walk(value, field="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            location = f"{field}.{key}"
            if _credential_key(key):
                yield _diagnostic("CREDENTIAL_FIELD", location, "credential", "Credential-shaped field is forbidden")
            yield from _walk(item, location)
    elif isinstance(value, list):
        for index, item in enumerate(value): yield from _walk(item, f"{field}[{index}]")


def _protected(path):
    if not isinstance(path, str) or not path.startswith("/") or ".." in PurePosixPath(path).parts:
        return True
    parts = PurePosixPath(path).parts
    protected_parts = {".ssh", ".aws", ".config", ".cache", "secrets", "credentials", "sessions", "logs", "runtime", "Keychains", "Caches", "Containers", "Group Containers"}
    return path == "/Users" or path.startswith("/Users/") or any(part.startswith(".") or part in protected_parts for part in parts)


def _unknown(mapping, allowed, field):
    return [_diagnostic("UNKNOWN_FIELD", f"{field}.{key}", "schema", "Unknown fields are forbidden") for key in mapping if key not in allowed]


def validate_plan(plan):
    """Return sorted, redacted structured diagnostics; an empty list is valid."""
    if not isinstance(plan, dict): return [_diagnostic("INVALID_PLAN", "$", "schema", "Plan must be an object")]
    errors = list(_walk(plan)) + _unknown(plan, EXPECTED, "$")
    for section in ("macbook", "mac_mini", "skills"):
        value = plan.get(section)
        if not isinstance(value, dict): errors.append(_diagnostic("INVALID_SECTION", section, "schema", "Section must be an object")); continue
        errors.extend(_unknown(value, NESTED[section], section))
    if plan.get("schema_version") != 1: errors.append(_diagnostic("INVALID_SCHEMA_VERSION", "schema_version", "schema", "schema_version must be 1"))
    macbook, mini, skills = plan.get("macbook", {}), plan.get("mac_mini", {}), plan.get("skills", {})
    if macbook.get("workspace_share_root") != "/Users/leo/projects": errors.append(_diagnostic("PROTECTED_PATH", "macbook.workspace_share_root", "share-root", "Only the canonical workspace root is eligible"))
    lock_root = macbook.get("lock_root")
    if not isinstance(lock_root, str) or not lock_root.startswith("/Users/Shared/") or "/projects" in lock_root or _protected(lock_root.replace("/Users/Shared", "/opt", 1)):
        errors.append(_diagnostic("INVALID_LOCK_ROOT", "macbook.lock_root", "lock-root", "Lock root must be local and outside SMB"))
    mount = mini.get("future_mount_target")
    if _protected(mount) or mount == "/Users/leo/projects": errors.append(_diagnostic("PROTECTED_PATH", "mac_mini.future_mount_target", "mount-target", "Mount target is protected or unsafe"))
    identity = mini.get("execution_identity", "")
    if not isinstance(identity, str) or not identity.strip() or "<" in identity or ">" in identity: errors.append(_diagnostic("PLACEHOLDER_IDENTITY", "mac_mini.execution_identity", "identity", "Execution identity must be a supplied account name"))
    if skills.get("transport") != "git": errors.append(_diagnostic("INVALID_TRANSPORT", "skills.transport", "skills", "Shared skills transport must be git"))
    url = skills.get("repository_url", ""); parsed = urlparse(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme not in ("https", "ssh") or parsed.username: errors.append(_diagnostic("INVALID_REPOSITORY_URL", "skills.repository_url", "skills", "Repository URL must be credential-free HTTPS or SSH"))
    roots = skills.get("local_clone_roots", {})
    if not isinstance(roots, dict): errors.append(_diagnostic("INVALID_CLONE_ROOTS", "skills.local_clone_roots", "skills", "Clone roots must be local paths"))
    else:
        errors.extend(_unknown(roots, NESTED["local_clone_roots"], "skills.local_clone_roots"))
        for role, root in roots.items():
            if _protected(root) or not isinstance(root, str) or not root.startswith("/"): errors.append(_diagnostic("PROTECTED_PATH", f"skills.local_clone_roots.{role}", "clone-root", "Clone root is unsafe"))
    areas, seen = plan.get("workspace_areas", []), []
    if not isinstance(areas, list) or not areas: errors.append(_diagnostic("INVALID_AREAS", "workspace_areas", "areas", "At least one area is required"))
    else:
        for index, area in enumerate(areas):
            if not isinstance(area, dict): errors.append(_diagnostic("INVALID_AREA", f"workspace_areas[{index}]", "areas", "Area must be an object")); continue
            errors.extend(_unknown(area, NESTED["area"], f"workspace_areas[{index}]")); area_id, relative = area.get("id", ""), area.get("relative_path", "")
            if not isinstance(area_id, str) or not AREA_ID.fullmatch(area_id): errors.append(_diagnostic("INVALID_AREA_ID", f"workspace_areas[{index}].id", "areas", "Area id is invalid"))
            if not isinstance(relative, str) or not relative or any(part in ("", ".", "..") for part in relative.split("/")): errors.append(_diagnostic("INVALID_AREA_PATH", f"workspace_areas[{index}].relative_path", "areas", "Area path is invalid"))
            for previous_id, previous_path in seen:
                if area_id == previous_id or relative == previous_path or relative.startswith(previous_path + "/") or previous_path.startswith(relative + "/"):
                    errors.append(_diagnostic("AREA_OVERLAP", f"workspace_areas[{index}]", "areas", "Area ids and paths must not overlap")); break
            seen.append((area_id, relative))
    return sorted(errors, key=lambda item: (item["code"], item["field"]))
