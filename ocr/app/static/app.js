const form = document.getElementById("cccd-form");
const message = document.getElementById("message");
const button = document.getElementById("submit-button");
const resultSection = document.getElementById("result-section");
const fields = document.getElementById("fields");
const warnings = document.getElementById("warnings");
const jsonOutput = document.getElementById("json-output");
const copyJson = document.getElementById("copy-json");

const labels = {
  so_cccd: "Số CCCD",
  ho_va_ten: "Họ và tên",
  ngay_sinh: "Ngày sinh",
  gioi_tinh: "Giới tính",
  quoc_tich: "Quốc tịch",
  que_quan: "Quê quán",
  noi_thuong_tru: "Nơi thường trú",
  ngay_het_han: "Ngày hết hạn",
  ngay_cap: "Ngày cấp",
  noi_cap: "Nơi cấp",
};

document.getElementById("front").addEventListener("change", (event) => preview(event, "front-preview"));
document.getElementById("back").addEventListener("change", (event) => preview(event, "back-preview"));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData();
  const frontFile = document.getElementById("front").files[0];
  const backFile = document.getElementById("back").files[0];
  formData.append("front", frontFile);
  if (backFile) {
    formData.append("back", backFile);
  }

  setMessage("Đang xử lý ảnh. Lần đầu chạy OCR có thể mất lâu hơn do tải model.", "");
  button.disabled = true;
  resultSection.classList.add("hidden");

  try {
    const response = await fetch("/api/read-cccd", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Không xử lý được ảnh.");
    }
    renderResult(payload);
    setMessage(`Đã xử lý xong. Mã lượt đọc: ${payload.id}`, "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    button.disabled = false;
  }
});

copyJson.addEventListener("click", async () => {
  await navigator.clipboard.writeText(jsonOutput.textContent);
  setMessage("Đã copy JSON.", "success");
});

function preview(event, imageId) {
  const file = event.target.files[0];
  const image = document.getElementById(imageId);
  if (!file) {
    image.removeAttribute("src");
    return;
  }
  image.src = URL.createObjectURL(file);
}

function renderResult(payload) {
  fields.innerHTML = "";
  warnings.innerHTML = "";

  for (const [key, label] of Object.entries(labels)) {
    const row = document.createElement("div");
    row.className = "field-row";
    row.innerHTML = `<span>${label}</span><strong>${escapeHtml(payload.data[key] || "")}</strong>`;
    fields.appendChild(row);
  }

  if (payload.warnings.length) {
    const list = document.createElement("ul");
    for (const warning of payload.warnings) {
      const item = document.createElement("li");
      item.textContent = warning;
      list.appendChild(item);
    }
    warnings.appendChild(list);
  }

  jsonOutput.textContent = JSON.stringify(payload.data, null, 2);
  resultSection.classList.remove("hidden");
}

function setMessage(text, type) {
  message.textContent = text;
  message.className = `message ${type}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
