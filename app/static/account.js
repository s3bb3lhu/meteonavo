const $=id=>document.getElementById(id),mode=location.pathname==='/account'?'account':location.pathname==='/login'?'login':'setup';
let csrf='';
try{sessionStorage.removeItem('weather-studio-admin-token');}catch(_){}
function message(text,success=false){$('message').textContent=text;$('message').classList.toggle('success',success);}
function nextPath(){const value=new URLSearchParams(location.search).get('next')||'/settings';return value==='/account'||value==='/'||/^\/settings(?:\/|\?|$)/.test(value)?value:'/settings';}
function rules(){const value=$('password').value,checks={length:value.length>=8,upper:/\p{Lu}/u.test(value),digit:/\p{Nd}/u.test(value),special:/[^\p{L}\p{N}\s]/u.test(value)};for(const item of document.querySelectorAll('[data-rule]'))item.classList.toggle('fulfilled',checks[item.dataset.rule]);}
if(mode==='login'){
 document.title='Meteonavo';$('account-title').textContent='Willkommen zurück';$('account-eyebrow').textContent='DEIN VERWALTUNGSZUGANG';$('account-description').textContent='Melde dich an, um deine Kanäle, Designs und Musik zu verwalten.';$('submit-account').textContent='Anmelden';$('password').autocomplete='current-password';$('password').removeAttribute('minlength');$('confirm-label').hidden=true;$('password-confirm').required=false;$('password-rules').hidden=true;$('setup-note').textContent='Deine Anmeldung bleibt für bis zu zwölf Stunden gültig.';
}else if(mode==='account'){
 document.title='Meteonavo';$('account-title').textContent='Mein Konto';$('account-eyebrow').textContent='DEINE ZUGANGSDATEN';$('account-description').textContent='Ändere deinen Benutzernamen oder dein Passwort. Bestätige die Änderung mit deinem aktuellen Passwort.';$('current-password-label').hidden=false;$('current-password').required=true;$('password-caption').textContent='Neues Passwort (leer lassen, um es beizubehalten)';$('password').required=false;$('password-confirm').required=false;$('submit-account').textContent='Zugangsdaten speichern';$('back-settings').hidden=false;$('setup-note').textContent='Nach einer Änderung werden alle bisherigen Anmeldungen beendet. Dieser Browser wird neu angemeldet.';
}
$('password').oninput=rules;
$('show-password').onchange=()=>{for(const id of ['password','password-confirm','current-password'])$(id).type=$('show-password').checked?'text':'password';};
$('account-form').onsubmit=async e=>{
 e.preventDefault();$('submit-account').disabled=true;message('');
 try{
  const data={username:$('username').value.trim(),password:$('password').value};
  if(mode!=='login'){data.password_confirm=$('password-confirm').value;if(data.password!==data.password_confirm)throw Error('Die Passwörter stimmen nicht überein.');}
  if(mode==='account')data.current_password=$('current-password').value;
  const response=await fetch('/api/auth/'+(mode==='account'?'account':mode),{method:mode==='account'?'PUT':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(data),credentials:'same-origin'});
  const result=await response.json();
  if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Bitte die Eingaben prüfen.');
  if(mode==='account'){csrf=result.csrf;$('current-password').value='';$('password').value='';$('password-confirm').value='';rules();message('Zugangsdaten gespeichert. Die bisherigen Sitzungen wurden beendet.',true);}
  else location.replace(mode==='setup'?'/settings':nextPath());
 }catch(error){message(error.message);}finally{$('submit-account').disabled=false;}
};
async function init(){const response=await fetch('/api/auth/status',{cache:'no-store'});const state=await response.json();csrf=state.csrf||'';if(!state.configured&&mode!=='setup')location.replace('/setup');else if(state.configured&&mode==='setup')location.replace(state.authenticated?'/settings':'/login');else if(mode==='account'){if(!state.authenticated)location.replace('/login?next=/account');else $('username').value=state.username;}else if(mode==='login'&&state.authenticated)location.replace(nextPath());}
init().catch(()=>message('Verbindung zum Studio nicht möglich. Bitte die Seite neu laden.'));
