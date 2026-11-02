// Runs zabbix/ha_notify_webhook.js against a mocked Zabbix runtime.
// Usage: node script_harness.js '<params json>' '<mock response json>' [status]
// Prints {"result": ..., "error": ..., "request": {...}} as JSON.
const fs = require('fs');
const path = require('path');

const code = fs.readFileSync(
    path.join(__dirname, '..', 'zabbix', 'ha_notify_webhook.js'), 'utf8');

const params = process.argv[2];
const mockResponse = process.argv[3] || '';
const mockStatus = parseInt(process.argv[4] || '200', 10);

const sent = {headers: [], proxy: null, url: null, body: null};

function HttpRequest() {}
HttpRequest.prototype.addHeader = function (h) { sent.headers.push(h); };
HttpRequest.prototype.setProxy = function (p) { sent.proxy = p; };
HttpRequest.prototype.post = function (url, body) {
    sent.url = url;
    sent.body = JSON.parse(body);
    return mockResponse;
};
HttpRequest.prototype.getStatus = function () { return mockStatus; };

const Zabbix = {log: function () {}};

let result = null;
let error = null;
try {
    result = new Function('value', 'HttpRequest', 'Zabbix', code)(params, HttpRequest, Zabbix);
} catch (e) {
    error = String(e);
}
console.log(JSON.stringify({result: result, error: error, request: sent}));
