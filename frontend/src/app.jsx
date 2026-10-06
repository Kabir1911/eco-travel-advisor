import React, {useState,useRef,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
const API='http://127.0.0.1:5005/webhooks/rest/webhook';
const welcome={role:'bot',text:"Welcome! Explore the Berlin travel demonstration. Choose Plan a trip to begin."};
const shortcuts=[['Plan a trip','/ask_destination'],['Hotels','/show_hotels'],['Transport','/show_transport'],['Destination guide','/destination_info'],['Weather','/show_weather'],['Convert budget to INR','Convert my budget to INR'],['Request advisor','/request_human']];
const money=x=>Number(x).toLocaleString('en-IE',{style:'currency',currency:'EUR'});
function HotelCarousel({cards}) {
 const [at,setAt]=useState(0);const card=cards[at];
 return <section className="carousel" aria-label="Fictional accommodation options">
  <div className="eyebrow">SIMULATED ACCOMMODATION</div>
  <div aria-live="polite"><h3>{card.name}</h3><p className="price">{money(card.total_price)} <small>for {card.nights} nights</small></p>
  <p>{money(card.nightly_price)} per night · One room, one traveller</p>
  <dl><dt>Remaining after accommodation</dt><dd>{money(card.remaining_budget)}</dd><dt>Near public transport</dt><dd>{card.near_public_transport?'Yes':'No'}</dd><dt>Certification</dt><dd>{card.certification}</dd></dl></div>
  <p className="fine">Fictional property and price. Availability is unverified. Transport, meals and other costs are extra; this does not confirm whole-trip affordability.</p>
  <nav aria-label="Hotel carousel controls"><button onClick={()=>setAt(at-1)} disabled={at===0}>← Previous</button><span>{at+1} of {cards.length}</span><button onClick={()=>setAt(at+1)} disabled={at===cards.length-1}>Next →</button></nav>
 </section>;
}
function App(){
 const [messages,setMessages]=useState([welcome]);const [input,setInput]=useState('');const [busy,setBusy]=useState(false);const [status,setStatus]=useState('Ready');const [handover,setHandover]=useState(false);
 const sender=useRef(crypto.randomUUID());const end=useRef(null);const locked=useRef(false);
 useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[messages,busy]);
 async function send(text,label=text){
  if(locked.current||!text.trim())return;locked.current=true;setBusy(true);setInput('');setStatus('Waiting for advisor…');
  setMessages(old=>[...old,{role:'user',text:label}]);
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),60000);
  try{
   const res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sender:sender.current,message:text}),signal:controller.signal});
   if(!res.ok)throw Error('HTTP '+res.status);
   const data=await res.json();if(!Array.isArray(data))throw Error('Unexpected reply');
   const values=data.map(r=>r.custom?.transport?.emissions_kg_co2e).filter(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0);
   const min=Math.min(...values),max=Math.max(...values);const replies=[];
   for(const reply of data){
    if(reply.custom?.hotel){
     if(replies.find(item=>item.hotels)?.hotels)replies.find(item=>item.hotels).hotels.push(reply.custom.hotel);
     else replies.push({role:'bot',hotels:[reply.custom.hotel]});continue;
    }
    const e=reply.custom?.transport?.emissions_kg_co2e;let carbon=null;
    if(reply.custom?.transport){
     if(typeof e!=='number'||!Number.isFinite(e)||e<0)carbon={tone:'unknown',label:'Emissions unavailable'};
     else if(values.length<2||max===min)carbon={tone:'neutral',label:'No relative emissions distinction'};
     else {const t=(e-min)/(max-min);carbon=t<=1/3?{tone:'low',label:'Lower relative emissions'}:t<=2/3?{tone:'medium',label:'Middle relative emissions'}:{tone:'high',label:'Higher relative emissions'};}
    }
    if(carbon&&!reply.text&&replies.length){replies[replies.length-1].carbon=carbon;continue;}const h=reply.custom?.handover;if(h)setHandover(true);
    if(reply.text||reply.buttons?.length||h||reply.image)replies.push({role:'bot',text:reply.text,buttons:reply.buttons,handover:h,carbon,image:reply.image});
   }
   setMessages(old=>[...old,...(replies.length?replies:[{role:'bot',text:'No reply was returned. Please rephrase your request.'}])]);setStatus('Ready');
  }catch(error){setMessages(old=>[...old,{role:'bot',text:'Could not get a reply. Check that Docker is running and the Rasa server is ready on port 5005. Please try again.'}]);setStatus('Connection problem');}
  finally{clearTimeout(timeout);locked.current=false;setBusy(false);}
 }
 function reset(){if(locked.current)return;sender.current=crypto.randomUUID();setMessages([welcome]);setHandover(false);setInput('');setStatus('Ready');}
 return <main><header><div className="eyebrow">BERLIN DEMONSTRATION</div><h1>Eco-Travel Advisor</h1><p>Explore travel choices with cost and carbon in view.</p></header>
 <aside className="notice">Prices and routes are fictional. Carbon estimates use reference factors. This prototype cannot book travel or contact an advisor.</aside>
 <section className="panel" aria-label="Travel chat"><div className="toolbar"><span role="status">{status}</span><button onClick={reset} disabled={busy}>New conversation</button></div>
 {handover&&<aside className="handover">Handover prepared locally for display. Nothing has been sent to an advisor.</aside>}
 <div className="chat" role="log" aria-label="Conversation" aria-live="polite">{messages.map((m,i)=><article key={i} className={'message '+m.role}>
 <strong className="speaker">{m.role==='user'?'You':'Eco-Travel Advisor'}</strong>
 {m.carbon&&<span className={'badge '+m.carbon.tone}>{m.carbon.label}</span>}
 {m.text&&<p className="message-text">{m.text}</p>}
 {m.hotels&&<HotelCarousel cards={m.hotels}/>}
 {m.image&&/^https:\/\//.test(m.image)&&<img className="reply-image" src={m.image} alt="Image supplied by the advisor"/>}
 {m.carbon&&<p className="fine">Relative to displayed estimates only. Colours use equal thirds of the emissions range; they are not official sustainability ratings. Missing estimates receive no rating.</p>}
 {!!m.buttons?.length&&<div className="choices">{m.buttons.map((b,j)=><button key={j} disabled={busy} onClick={()=>send(b.payload,b.title)}>{b.title}</button>)}</div>}
 {m.handover&&<details><summary>View prepared trip details and conversation</summary><pre>{JSON.stringify(m.handover,null,2)}</pre></details>}
 </article>)}{busy&&<p className="thinking">Preparing your response…</p>}<div ref={end}/></div>
 <div className="shortcuts" aria-label="Travel shortcuts">{shortcuts.map(([title,payload])=><button key={title} disabled={busy} onClick={()=>send(payload,title)}>{title}</button>)}</div>
 <form onSubmit={e=>{e.preventDefault();send(input);}}><label htmlFor="message">Your message</label><div className="input-row"><input id="message" autoComplete="off" maxLength={1000} value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask about your trip…" disabled={busy}/><button className="primary" type="submit" disabled={busy||!input.trim()}>Send</button></div></form></section>
 <footer>Demo route: Frankfurt → Berlin. Use dates like “from 2026-11-10 to 2026-11-15”. Avoid sensitive personal information. New conversation starts a fresh session; it does not delete server history.</footer></main>;
}
createRoot(document.getElementById('root')).render(<App/>);
