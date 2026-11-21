// Shared AJAX plumbing for CSRF-protected POSTs.
// Used by the chat like button and the map's share-to-chat handler.

function getCsrfToken() {
  const input = document.querySelector("input[name=csrfmiddlewaretoken]");
  return (
    input?.value ||
    document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith("csrftoken="))
      ?.split("=")[1] ||
    null
  );
}

// POST JSON-ish data with the CSRF header; returns parsed JSON.
// Throws on non-2xx so callers can catch and surface the failure.
async function postJSON(url, data) {
  const token = getCsrfToken();
  if (!token) throw new Error("No CSRF token available");
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "X-CSRFToken": token,
      "X-Requested-With": "XMLHttpRequest",
    },
    body: data,
  });
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  return resp.json();
}
