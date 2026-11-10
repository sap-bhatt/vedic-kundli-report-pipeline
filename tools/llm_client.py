"""Minimal LLM client for the kundli-report runner (tools/run_report.py). Standard library only (urllib, json).

  from llm_client import complete
  text, usage = complete(messages, system, model, provider, base_url, max_tokens, temperature)

messages: [{"role": "user"|"assistant", "content": "..."}]. system: a string (may be empty).
provider:
  anthropic  Anthropic Messages API: POST {base_url or https://api.anthropic.com}/v1/messages with x-api-key and
             anthropic-version headers. Key from ANTHROPIC_API_KEY.
  openai     Any OpenAI-compatible endpoint: POST {base_url or https://api.openai.com/v1}/chat/completions with a Bearer
             key from OPENAI_API_KEY or LLM_API_KEY (DeepSeek, Qwen, OpenRouter, vLLM, Ollama, ...). A local server
             without auth works with no key set.
temperature: None leaves it out of the request. Current Claude models reject temperature (HTTP 400), so the runner
             sends None for provider anthropic by default.
usage: {"input_tokens" (including cached), "output_tokens", "cache_read_tokens", "estimated": bool, "stop": stop
       reason, "attempts": HTTP attempts}. When the
       API returns no usage, tokens are estimated as chars/4 and estimated is True.
Retries with exponential backoff (honouring Retry-After) on 408/409/429/5xx and network errors; other HTTP errors raise
LLMError at once with the response body.
"""
import json, os, random, socket, time, urllib.error, urllib.request

ANTHROPIC_VERSION = '2023-06-01'
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class LLMError(RuntimeError):
    pass


def est_tokens(s):
    return max(1, len(s or '') // 4)


def _post(url, headers, body, timeout, max_retries):
    data = json.dumps(body).encode('utf-8')
    delay, attempt = 2.0, 0
    while True:
        attempt += 1
        req = urllib.request.Request(url, data=data, method='POST',
                                     headers={'content-type': 'application/json', **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8')), attempt
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:2000]
            if e.code not in RETRY_STATUS or attempt > max_retries:
                raise LLMError(f'HTTP {e.code} from {url}: {msg}')
            ra = e.headers.get('retry-after') if e.headers else None
            try:
                wait = float(ra) if ra else delay
            except ValueError:
                wait = delay
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            if attempt > max_retries:
                raise LLMError(f'network error calling {url}: {e}')
            wait = delay
        time.sleep(min(wait, 120) + random.uniform(0, 1))
        delay = min(delay * 2, 120)


def complete(messages, system, model, provider='anthropic', base_url=None, max_tokens=6000, temperature=None,
             timeout=900, max_retries=5, extra=None, api_key=None):
    """One chat completion -> (text, usage). extra: dict merged into the request body (e.g. provider-specific
    fields such as {"output_config": {"effort": "low"}} or {"max_completion_tokens": 6000})."""
    provider = (provider or 'anthropic').lower()
    if provider == 'anthropic':
        key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not key: raise LLMError('ANTHROPIC_API_KEY is not set')
        url = (base_url or 'https://api.anthropic.com').rstrip('/')
        url = url if url.endswith('/v1/messages') else url + '/v1/messages'
        body = {'model': model, 'max_tokens': max_tokens, 'messages': messages}
        if system: body['system'] = system
        if temperature is not None: body['temperature'] = temperature
        body.update(extra or {})
        resp, n = _post(url, {'x-api-key': key, 'anthropic-version': ANTHROPIC_VERSION}, body, timeout, max_retries)
        text = ''.join(b.get('text', '') for b in resp.get('content', []) if b.get('type') == 'text')
        u = resp.get('usage') or {}
        inp = u.get('input_tokens')
        cache_read = u.get('cache_read_input_tokens') or 0
        if inp is not None:
            inp += cache_read + (u.get('cache_creation_input_tokens') or 0)
        stop = resp.get('stop_reason')
    elif provider in ('openai', 'openai-compatible', 'compatible'):
        key = api_key or os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY')
        url = (base_url or 'https://api.openai.com/v1').rstrip('/')
        url = url if url.endswith('/chat/completions') else url + '/chat/completions'
        msgs = ([{'role': 'system', 'content': system}] if system else []) + list(messages)
        body = {'model': model, 'messages': msgs, 'max_tokens': max_tokens}
        if temperature is not None: body['temperature'] = temperature
        body.update(extra or {})
        if 'max_completion_tokens' in body: body.pop('max_tokens', None)
        resp, n = _post(url, {'authorization': f'Bearer {key}'} if key else {}, body, timeout, max_retries)
        ch = (resp.get('choices') or [{}])[0]
        text = ((ch.get('message') or {}).get('content')) or ''
        u = resp.get('usage') or {}
        inp = u.get('prompt_tokens')
        cache_read = ((u.get('prompt_tokens_details') or {}).get('cached_tokens')) or 0
        u = {'output_tokens': u.get('completion_tokens')}
        stop = ch.get('finish_reason')
    else:
        raise LLMError(f'unknown provider {provider!r}')
    out_t = u.get('output_tokens')
    estimated = inp is None or out_t is None
    if inp is None: inp = est_tokens(system) + sum(est_tokens(m['content']) for m in messages)
    if out_t is None: out_t = est_tokens(text)
    return text, {'input_tokens': inp, 'output_tokens': out_t, 'estimated': estimated, 'cache_read_tokens': cache_read,
                  'stop': stop, 'attempts': n}
