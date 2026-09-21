from app.codes import CODE_LENGTH


def create(client, headers, url="https://www.python.org/downloads/"):
    return client.post("/links", json={"url": url}, headers=headers)


def test_create_link_requires_login(client):
    response = client.post("/links", json={"url": "https://example.org"})
    assert response.status_code == 401


def test_create_link(client, make_user):
    headers = make_user()
    response = create(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == CODE_LENGTH
    assert body["target_url"] == "https://www.python.org/downloads/"
    assert body["short_url"].endswith("/" + body["code"])


def test_create_rejects_bad_urls(client, make_user):
    headers = make_user()
    for bad in ["javascript:alert(1)", "www.python.org", "ftp://example.org/file", "", "nonsense"]:
        assert create(client, headers, bad).status_code == 422, bad


def test_redirect_sends_browser_to_target(client, make_user):
    code = create(client, make_user()).json()["code"]
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://www.python.org/downloads/"


def test_redirect_is_public_no_login_needed(client, make_user):
    code = create(client, make_user()).json()["code"]
    assert client.get(f"/{code}", follow_redirects=False).status_code == 302


def test_redirect_unknown_code_is_404(client):
    assert client.get("/AAAAAAA", follow_redirects=False).status_code == 404


def test_redirect_badly_formatted_code_is_404(client):
    assert client.get("/abc", follow_redirects=False).status_code == 404
    assert client.get("/waytoolongcode", follow_redirects=False).status_code == 404


def test_other_routes_are_not_swallowed_by_redirect(client):
    assert client.get("/health").status_code == 200
    assert client.get("/links").status_code == 401  # the links route, not a 404 from redirect


def test_list_shows_only_my_links_newest_first(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    create(client, alice, "https://first.example/")
    create(client, alice, "https://second.example/")
    create(client, bob, "https://bobs.example/")

    mine = client.get("/links", headers=alice).json()
    assert [link["target_url"] for link in mine] == [
        "https://second.example/",
        "https://first.example/",
    ]
    theirs = client.get("/links", headers=bob).json()
    assert [link["target_url"] for link in theirs] == ["https://bobs.example/"]


def test_list_pagination(client, make_user):
    headers = make_user()
    for i in range(5):
        create(client, headers, f"https://site{i}.example/")
    page1 = client.get("/links?limit=2&offset=0", headers=headers).json()
    page2 = client.get("/links?limit=2&offset=2", headers=headers).json()
    page3 = client.get("/links?limit=2&offset=4", headers=headers).json()
    assert [len(page1), len(page2), len(page3)] == [2, 2, 1]
    all_codes = [link["code"] for link in page1 + page2 + page3]
    assert len(set(all_codes)) == 5


def test_list_rejects_out_of_range_limit(client, make_user):
    headers = make_user()
    assert client.get("/links?limit=1000", headers=headers).status_code == 422
    assert client.get("/links?limit=0", headers=headers).status_code == 422
    assert client.get("/links?offset=-1", headers=headers).status_code == 422


def test_delete_own_link_then_redirect_stops_working(client, make_user):
    headers = make_user()
    code = create(client, headers).json()["code"]
    assert client.delete(f"/links/{code}", headers=headers).status_code == 204
    assert client.get(f"/{code}", follow_redirects=False).status_code == 404
    assert client.get("/links", headers=headers).json() == []


def test_cannot_delete_someone_elses_link(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    code = create(client, alice).json()["code"]

    assert client.delete(f"/links/{code}", headers=bob).status_code == 404
    assert client.get(f"/{code}", follow_redirects=False).status_code == 302  # still alive


def test_delete_unknown_code_is_404(client, make_user):
    assert client.delete("/links/AAAAAAA", headers=make_user()).status_code == 404


def test_delete_requires_login(client, make_user):
    code = create(client, make_user()).json()["code"]
    assert client.delete(f"/links/{code}").status_code == 401


def test_code_collision_is_retried_with_a_new_code(client, make_user, monkeypatch):
    headers = make_user()
    # First link takes "AAAAAAA". The next link's generator returns "AAAAAAA" twice
    # (both collide with the existing link) and then a fresh code.
    codes = iter(["AAAAAAA", "AAAAAAA", "AAAAAAA", "BBBBBBB"])
    monkeypatch.setattr("app.routers.links.generate_code", lambda: next(codes))

    first = create(client, headers, "https://first.example/")
    second = create(client, headers, "https://second.example/")

    assert first.json()["code"] == "AAAAAAA"
    assert second.status_code == 201
    assert second.json()["code"] == "BBBBBBB"
    assert client.get("/BBBBBBB", follow_redirects=False).headers["location"] == (
        "https://second.example/"
    )


def test_gives_up_with_503_when_every_code_collides(client, make_user, monkeypatch):
    headers = make_user()
    monkeypatch.setattr("app.routers.links.generate_code", lambda: "AAAAAAA")
    assert create(client, headers).status_code == 201
    assert create(client, headers, "https://other.example/").status_code == 503
