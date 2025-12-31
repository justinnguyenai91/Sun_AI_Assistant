export async function chat({ baseUrl, apiKey, model, messages, ...opts }) {
  const url = `${baseUrl.replace(/\/$/,'')}/v1/chat/completions`;
  const body = JSON.stringify({ model, messages, ...opts });
  for (let i=0;i<3;i++){
    const res = await fetch(url, {
      method:'POST',
      headers:{
        'Content-Type':'application/json',
        'Authorization':`Bearer ${apiKey}`
      },
      body
    });
    if (res.status === 429 && i<2) { 
      await new Promise(r=>setTimeout(r, 1500*(i+1)));
      continue;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return await res.json();
  }
}
