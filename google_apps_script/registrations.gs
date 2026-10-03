/**
 * Telegram botdan kelgan ro'yxatdan o'tganlarni Google Sheets'ga yozadi.
 *
 * O'rnatish: README.md dagi "Google Sheets" bo'limiga qarang.
 * Maxfiy kalit "Script properties" ichida SECRET nomi bilan saqlanadi
 * (botdagi SHEETS_SECRET bilan bir xil bo'lishi kerak).
 */
const SHEET_NAME = "Ro'yxatdan o'tganlar";
const HEADERS = [
  "Telegram ID", "Username", "F.I.Sh.", "Telefon", "Pasport", "HEMIS ID", "Ro'yxatdan o'tgan vaqt",
];

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonOutput({ ok: false, error: "bad_request" });
  }

  const secret = PropertiesService.getScriptProperties().getProperty("SECRET");
  if (!secret || body.secret !== secret) {
    return jsonOutput({ ok: false, error: "unauthorized" });
  }

  const r = body.record || {};
  const values = [
    String(r.telegram_id || ""),
    r.username ? "@" + r.username : "",
    r.full_name || "",
    r.phone || "",
    r.passport || "",
    r.hemis_id || "",
    r.registered_at || "",
  ];
  if (!values[0] || !values[5]) {
    return jsonOutput({ ok: false, error: "bad_record" });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.setFrozenRows(1);
      sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight("bold");
    }

    // Shu Telegram ID bilan qator bo'lsa yangilanadi, bo'lmasa yangi qator qo'shiladi
    const lastRow = sheet.getLastRow();
    let row = lastRow + 1;
    if (lastRow > 1) {
      const ids = sheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues();
      for (let i = 0; i < ids.length; i++) {
        if (ids[i][0] === values[0]) {
          row = i + 2;
          break;
        }
      }
    }

    const range = sheet.getRange(row, 1, 1, values.length);
    range.setNumberFormat("@"); // telefon, pasport va HEMIS ID matn sifatida saqlansin
    range.setValues([values]);
    return jsonOutput({ ok: true, row: row });
  } finally {
    lock.releaseLock();
  }
}
