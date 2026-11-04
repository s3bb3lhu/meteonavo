"""Address results must match place/street names, not merely a house number."""
import re
import unicodedata
from difflib import SequenceMatcher
from .regions import COUNTRIES

def plain(value):
    return unicodedata.normalize('NFKD',str(value or '').casefold()).encode('ascii','ignore').decode()

STOP=set('urbanizacion urbanitzacio urbanization urb calle carrer avenida av avda carretera paseo passeig plaza placa de del la las los el en espana spain'.split())
MARKER=re.compile(r'\b(?:urbanizacion|urbanitzacio|calle|carrer|avenida|carretera|paseo|passeig|plaza|placa)\b')

def spanish_query(query):
    query=re.sub(r'\b(?:urbanicazion|urbanisacion|urb)(?:\.)?(?=\s|$)','Urbanización',query,flags=re.I)
    marker=MARKER.search(plain(query))
    if marker and marker.start()>0:
        prefix=query[:marker.start()].strip(' ,')
        # Common input order: town, urbanisation/street, number.
        if prefix and not any(c.isdigit() for c in prefix):
            query=query[marker.start():].strip()+', '+prefix
    return query.strip()

def queries(query,country):
    if country!='ES':return [query.strip()]
    first=spanish_query(query)
    # Retain postcode and named area; dropping an unavailable house number must
    # yield an explicitly approximate result, never a fabricated house point.
    broad=re.sub(r'(?<!\w)\d{1,4}\s?[a-z]?(?!\w)',' ',first,flags=re.I)
    broad=re.sub(r'\s+',' ',broad).replace(' ,',',').strip(' ,')
    return list(dict.fromkeys(q for q in [first,broad] if len(q)>=3))

def words(value):
    return [w for w in re.findall(r'[a-z]+',plain(value)) if len(w)>2 and w not in STOP]

def similar(word,values):
    return any(word==v or min(len(word),len(v))>=4 and SequenceMatcher(None,word,v).ratio()>=.86 for v in values)

def matching(properties,query,country):
    if country!='ES':return True
    normalized=spanish_query(query);wanted=words(normalized)
    available=words(' '.join(str(properties.get(k,'') or '') for k in ['name','street','locality','district','city','town','village']))
    if wanted:
        hits=sum(similar(w,available) for w in wanted)
        if hits<max(1,len(wanted)-(1 if len(wanted)>=3 else 0)):return False
    prefix=MARKER.search(plain(query))
    if prefix and prefix.start()>0:
        town=words(query[:prefix.start()]);city=words(properties.get('city') or properties.get('town') or properties.get('village'))
        if town and not all(similar(w,city) for w in town):return False
    numbers=re.findall(r'(?<!\w)(\d{1,4}\s?[a-z]?)(?!\w)',query,flags=re.I)
    house=properties.get('housenumber')
    if house and numbers and plain(house).replace(' ','') not in [plain(n).replace(' ','') for n in numbers]:return False
    return True

def results(features,query,country):
    output=[];seen=set()
    for f in features:
        p=f.get('properties',{});coords=f.get('geometry',{}).get('coordinates',[])
        if p.get('countrycode','').upper()!=country or len(coords)<2:continue
        if country=='ES' and p.get('osm_key') in ['waterway','natural']:continue
        if not matching(p,query,country):continue
        street=' '.join(str(p.get(k,'') or '') for k in ['street','housenumber']).strip()
        city=p.get('city') or p.get('town') or p.get('village') or p.get('name','')
        precision='house' if p.get('housenumber') else 'street' if p.get('street') or p.get('type')=='street' else 'locality' if p.get('type') in ['locality','district'] else 'place'
        label=', '.join(dict.fromkeys(v for v in [street or p.get('name',''),p.get('locality',''),p.get('district',''),' '.join([str(p.get('postcode','') or ''),city]).strip(),p.get('state',''),COUNTRIES[country]] if v))
        identity=(label,coords[0],coords[1])
        if identity in seen:continue
        seen.add(identity)
        note='' if precision=='house' else 'Ungefährer Treffer: Die angefragte Hausnummer ist nicht bestätigt. GPS-Punkt vor dem Speichern prüfen.'
        output.append(dict(address=label,location=city,latitude=coords[1],longitude=coords[0],country_code=country,state=p.get('state',''),county=p.get('county',''),precision=precision,precision_note=note))
    return output

async def search(client,url,query,country,throttle):
    for candidate in queries(query,country):
        await throttle()
        # Provider rejections propagate; alternative spellings never bypass them.
        response=await client.get(url,params={'q':candidate,'countrycode':country,'lang':'de','limit':15})
        response.raise_for_status()
        found=results(response.json().get('features',[]),query,country)
        if found:return found
    return []
