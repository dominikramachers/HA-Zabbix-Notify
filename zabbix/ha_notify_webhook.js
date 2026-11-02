/*
 * ha-zabbix-notify: Zabbix webhook media type for Home Assistant.
 *
 * Posts problem, update and recovery events as JSON to the webhook of the
 * "Zabbix Notify" integration. Written in ES5 (Zabbix uses Duktape).
 */
var UNKNOWN = '*UNKNOWN*';

function isUnresolvedMacro(value) {
    return /^\{\$?[A-Za-z0-9_.:#]+\}$/.test(value);
}

function clean(value) {
    if (value === undefined || value === null) {
        return '';
    }
    value = String(value).replace(/^\s+|\s+$/g, '');
    if (value === UNKNOWN || isUnresolvedMacro(value)) {
        return '';
    }
    return value;
}

function parseTags(raw) {
    raw = clean(raw);
    if (raw === '') {
        return [];
    }
    try {
        var parsed = JSON.parse(raw);
        return Object.prototype.toString.call(parsed) === '[object Array]' ? parsed : [];
    }
    catch (error) {
        return [];
    }
}

function kindOf(params) {
    if (clean(params.event_update_status) === '1') {
        return 'update';
    }
    if (clean(params.event_value) === '1') {
        return 'problem';
    }
    return 'resolved';
}

function buildPayload(params) {
    var eventId = clean(params.event_id);
    if (eventId === '') {
        // Zabbix does not resolve event macros in the media type "Test" dialog.
        return {version: 1, kind: 'test'};
    }

    var source = clean(params.event_source);
    if (source !== '' && source !== '0' && source !== '3') {
        throw 'Unsupported event source ' + source +
            '. Only trigger (0) and internal (3) events are supported.';
    }

    return {
        version: 1,
        kind: kindOf(params),
        event_id: eventId,
        trigger_id: clean(params.trigger_id),
        event_name: clean(params.event_name),
        host: clean(params.host_name),
        severity: clean(params.event_nseverity),
        opdata: clean(params.event_opdata),
        update_action: clean(params.event_update_action),
        update_message: clean(params.event_update_message),
        update_user: clean(params.event_update_user),
        duration: clean(params.event_duration),
        age: clean(params.event_age),
        event_time: clean(params.event_time),
        zabbix_url: clean(params.zabbix_url),
        tags: parseTags(params.event_tagsjson)
    };
}

try {
    var params = JSON.parse(value);

    var url = clean(params.url);
    var token = clean(params.token);
    if (url === '') {
        throw 'Parameter "url" is empty. Define the macro {$HA_NOTIFY_URL} or edit the parameter.';
    }
    if (token === '') {
        throw 'Parameter "token" is empty. Define the macro {$HA_NOTIFY_TOKEN} or edit the parameter.';
    }

    var payload = buildPayload(params);

    var request = new HttpRequest();
    request.addHeader('Content-Type: application/json');
    request.addHeader('X-Zabbix-Notify-Token: ' + token);

    var proxy = clean(params.http_proxy);
    if (proxy !== '') {
        request.setProxy(proxy);
    }

    Zabbix.log(4, '[ha-zabbix-notify] sending ' + payload.kind + ' event ' + (payload.event_id || '(test)'));
    var response = request.post(url, JSON.stringify(payload));
    var status = request.getStatus();
    if (status < 200 || status > 299) {
        throw 'HTTP ' + status + ': ' + response;
    }

    // Home Assistant answers 200 with an empty body for unknown webhook IDs,
    // so check for our own confirmation.
    var answer = null;
    try {
        answer = JSON.parse(response);
    }
    catch (error) {
        answer = null;
    }
    if (answer === null || answer.ok !== true) {
        throw 'Unexpected response, check the webhook ID in the URL: ' + response;
    }

    return 'OK: ' + payload.kind;
}
catch (error) {
    Zabbix.log(3, '[ha-zabbix-notify] sending failed: ' + error);
    throw 'Sending to Home Assistant failed: ' + error;
}
