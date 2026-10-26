/** Native browser actions. The backend captures selected request and result fields. */
const element = (id) => document.getElementById(id);
let reviewedVersion = null;

async function request(action, values) {
  const response = await fetch("/app/" + action, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  if (!response.ok) throw Error("Request failed: " + response.status);
  return response.json();
}

async function uploadImage() {
  const file = element("image").files[0];
  if (!file) return;
  const bytes = new Uint8Array(await file.arrayBuffer());
  const image = btoa(Array.from(bytes, (value) => String.fromCharCode(value)).join(""));
  const result = await request("upload", { actor: "artist", title: element("title").value, image });
  element("upload-result").textContent = JSON.stringify(result, null, 2);
}

async function openReview() {
  const result = await request("preview", { actor: "reviewer" });
  reviewedVersion = result.reviewed_version;
  element("review-version").textContent = "Opened version " + reviewedVersion;
  element("review-image").src = "/artwork.png?version=" + reviewedVersion;
  element("review-image").hidden = false;
  element("approve").disabled = false;
  element("review-result").textContent = JSON.stringify(result, null, 2);
}

async function approveReview() {
  const result = await request("approve", { actor: "reviewer", reviewed_version: reviewedVersion });
  element("review-result").textContent = JSON.stringify(result, null, 2);
  await refreshExhibition();
}

async function refreshExhibition() {
  const result = await request("public", {});
  element("public-version").textContent = result.published_version
    ? "Published version " + result.published_version
    : "Nothing published";
  element("public-image").hidden = !result.published_version;
  if (result.published_version)
    element("public-image").src = "/artwork.png?version=" + result.published_version;
  element("messages").textContent = result.messages
    .map((version) => "Version " + version + " ready for review")
    .join(" · ");
}

/** Surface application failures in the panel used by the person taking the action. */
function action(id, execute, output) {
  element(id).onclick = () =>
    execute().catch((error) => {
      element(output).textContent = error.message;
    });
}
action("upload", uploadImage, "upload-result");
action("preview", openReview, "review-result");
action("approve", approveReview, "review-result");
action("refresh", refreshExhibition, "messages");
