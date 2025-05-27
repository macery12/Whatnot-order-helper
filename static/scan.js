
import {
  BrowserMultiFormatReader,
  BrowserCodeReader
} from 'https://cdn.jsdelivr.net/npm/@zxing/browser@0.0.10/+esm';

const codeReader = new BrowserMultiFormatReader();
const scannerContainer = document.getElementById('scanner');
const modal = document.getElementById('matchModal');
const foundTracking = document.getElementById('foundTracking');
const status = document.getElementById('status');
let scanned = false;

async function startScanner() {
  scanned = false;
  status.textContent = "📷 Scanning...";
  try {
    const devices = await BrowserCodeReader.listVideoInputDevices();
    const backCam = devices.find(d => d.label.toLowerCase().includes('back')) || devices[0];

    await codeReader.decodeFromVideoDevice(backCam.deviceId, scannerContainer, (result, err) => {
      if (result && !scanned) {
        scanned = true;
        const code = result.text;
        status.textContent = "✅ Scan successful!";
        codeReader.reset();
        showModal(code);
      }
    });
  } catch (e) {
    console.error(e);
    status.textContent = "❌ Could not access camera.";
  }
}

function showModal(code) {
  foundTracking.textContent = "Tracking: " + code;
  document.getElementById("viewDetails").onclick = () => {
    window.location.href = "/details?tracking=" + code;
  };
  modal.style.display = "flex";
}

document.getElementById("retryScan").onclick = () => {
  modal.style.display = "none";
  startScanner();
};

window.onload = startScanner;
