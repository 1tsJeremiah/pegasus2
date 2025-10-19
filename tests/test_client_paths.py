from codex_vector.client import CodexVectorClient

def test_tenant_path_building():
    c = CodexVectorClient(base_url="http://localhost:8000/api/v2", tenant="tn", database="db")
    adapter = c._adapter  # type: ignore[attr-defined]
    assert adapter._tenant_path("/collections") == "/tenants/tn/databases/db/collections"  # type: ignore[attr-defined]

def test_base_url_trim_regression():
    c = CodexVectorClient(base_url="http://localhost:8000/api/v2/", tenant="tn", database="db")
    assert c.base_url == "http://localhost:8000/api/v2"
    adapter = c._adapter  # type: ignore[attr-defined]
    assert adapter._tenant_path("/x") == "/tenants/tn/databases/db/x"  # type: ignore[attr-defined]
