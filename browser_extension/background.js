/* global chrome */
'use strict';

let nativePort = null;
let reconnectTimer = null;

function connectNative() {
  if (nativePort) {
    try { nativePort.disconnect(); } catch (e) {}
  }
  try {
    nativePort = chrome.runtime.connectNative('com.realtimix.host');
    nativePort.onMessage.addListener((msg) => {
      chrome.tabs.query({}, (tabs) => {
        for (const tab of tabs) {
          chrome.tabs.sendMessage(tab.id, {from: 'host', data: msg}).catch(() => {});
        }
      });
    });
    nativePort.onDisconnect.addListener(() => {
      nativePort = null;
      if (!reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connectNative();
        }, 3000);
      }
    });
  } catch (e) {
    nativePort = null;
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectNative();
      }, 3000);
    }
  }
}

connectNative();

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (nativePort) {
    nativePort.postMessage(request);
    sendResponse({status: 'sent'});
  } else {
    sendResponse({status: 'error', message: 'Native host not connected. Is RealTimeMix running?'});
  }
  return true;
});
