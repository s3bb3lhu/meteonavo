from test_api import studio,AUTH

def test_approved_concepts_and_backgrounds_persist_per_channel(studio):
    client,m=studio
    original=m.get_channel(2)
    for theme in ['panorama-glass','editorial-light','ruby-broadcast','forest-terrain','retro-broadcast','retro-digital','aurora-gradient','alpine-luxe']:
        r=client.patch('/api/channels/1',headers=AUTH,json=dict(theme=theme,landscape_mood='auto',color='#aabbcc'))
        assert r.status_code==200 and m.get_channel(1)['theme']==theme and r.json()['color']=='#aabbcc'
    for mood in ['off','auto','dawn','day','rain','dusk','night','snow']:
        assert client.patch('/api/channels/1',headers=AUTH,json=dict(landscape_mood=mood)).json()['landscape_mood']==mood
    assert client.patch('/api/channels/1',headers=AUTH,json=dict(landscape_mood='imaginary')).status_code==422
    assert m.get_channel(2)==original


def test_frame_styles_persist_independently_of_design(studio):
    client,m=studio
    before=m.get_channel(2)
    client.patch('/api/channels/1',headers=AUTH,json=dict(theme='panorama-glass',landscape_mood='auto'))
    for frame in ['design','fine-line','broadcast-edge','contour','retro-chrome','soft-ribbon','corner-brackets']:
        r=client.patch('/api/channels/1',headers=AUTH,json=dict(frame_style=frame))
        assert r.status_code==200 and m.get_channel(1)['frame_style']==frame
        assert r.json()['theme']=='panorama-glass' and r.json()['landscape_mood']=='auto'
    assert client.patch('/api/channels/1',headers=AUTH,json=dict(frame_style='unknown')).status_code==422
    assert m.get_channel(2)==before


def test_frame_customization_validation_and_channel_isolation(studio):
    client,m=studio
    before=m.get_channel(2)
    patch=dict(frame_style='fine-line',frame_custom=True,frame_color='#12abef',frame_width=8,frame_radius=0,frame_opacity=20)
    r=client.patch('/api/channels/1',headers=AUTH,json=patch)
    assert r.status_code==200
    assert all(m.get_channel(1)[key]==value for key,value in patch.items())
    for key,value in [('frame_width',9),('frame_width',0),('frame_radius',49),('frame_opacity',19),('frame_color','red')]:
        assert client.patch('/api/channels/1',headers=AUTH,json={key:value}).status_code==422
    assert client.patch('/api/channels/1',headers=AUTH,json={'frame_custom':False}).json()['frame_color']=='#12abef'
    assert m.get_channel(2)==before
