"""Europe, including microstates, dependencies and transcontinental neighbours."""
COUNTRIES = dict(sorted({
 'AL':'Albanien','AD':'Andorra','AM':'Armenien','AZ':'Aserbaidschan','AT':'Österreich',
 'BY':'Belarus','BE':'Belgien','BA':'Bosnien und Herzegowina','BG':'Bulgarien','CY':'Zypern',
 'CZ':'Tschechien','DE':'Deutschland','DK':'Dänemark','EE':'Estland','ES':'Spanien',
 'FI':'Finnland','FR':'Frankreich','GE':'Georgien','GR':'Griechenland','HR':'Kroatien',
 'HU':'Ungarn','IE':'Irland','IS':'Island','IT':'Italien','KZ':'Kasachstan','XK':'Kosovo',
 'LI':'Liechtenstein','LT':'Litauen','LU':'Luxemburg','LV':'Lettland','MC':'Monaco',
 'MD':'Moldau','ME':'Montenegro','MK':'Nordmazedonien','MT':'Malta','NL':'Niederlande',
 'NO':'Norwegen','PL':'Polen','PT':'Portugal','RO':'Rumänien','RS':'Serbien','RU':'Russland',
 'SE':'Schweden','SI':'Slowenien','SK':'Slowakei','SM':'San Marino','CH':'Schweiz',
 'TR':'Türkei','UA':'Ukraine','GB':'Vereinigtes Königreich','VA':'Vatikanstadt',
 'AX':'Åland','FO':'Färöer','GI':'Gibraltar','GG':'Guernsey','JE':'Jersey','IM':'Isle of Man',
 'SJ':'Svalbard und Jan Mayen'}.items(), key=lambda x:x[1]))
STATES = ['Baden-Württemberg','Bayern','Berlin','Brandenburg','Bremen','Hamburg','Hessen',
 'Mecklenburg-Vorpommern','Niedersachsen','Nordrhein-Westfalen','Rheinland-Pfalz','Saarland',
 'Sachsen','Sachsen-Anhalt','Schleswig-Holstein','Thüringen']
ALIASES = {'bavaria':'Bayern','hesse':'Hessen','lower saxony':'Niedersachsen',
 'north rhine-westphalia':'Nordrhein-Westfalen','rhineland-palatinate':'Rheinland-Pfalz',
 'saxony':'Sachsen','saxony-anhalt':'Sachsen-Anhalt','thuringia':'Thüringen',
 'baden-wurttemberg':'Baden-Württemberg','mecklenburg-western pomerania':'Mecklenburg-Vorpommern'}

def german_state(value):
    text=(value or '').strip().casefold()
    return next((s for s in STATES if s.casefold()==text), ALIASES.get(text,''))
