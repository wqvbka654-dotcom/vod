let host = 'https://www.kanbook.cc';
let headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.31 Mobile Safari/537.36',
};

function getList(html) {
    return pdfa(html, '.card').map(it => ({
        vod_id: pdfh(it, 'a&&href'),
        vod_name: pdfh(it, 'img&&alt'),
        vod_pic: (pic => pic?.startsWith('/') ? host + pic : pic)(pd(it, 'img&&data-original', host)),
        vod_remarks: pdfh(it, '.label&&Text')
    }));
}

async function init(cfg) {}

async function home(filter) {
    return JSON.stringify({
        class: [{
            "type_id": "1",
            "type_name": "电影"
        }, {
            "type_id": "2",
            "type_name": "电视剧"
        }, {
            "type_id": "3",
            "type_name": "综艺"
        }, {
            "type_id": "4",
            "type_name": "动漫"
        },{
            "type_id": "23",
            "type_name": "短剧"
        }],
        filters: {       
        }
    });
}    

async function homeVod() {
    let resp = await req(host, {
        headers
    });
    return JSON.stringify({
        list: getList(resp.content)
    });
}

async function category(tid, pg, filter, extend) {
    let p = pg || 1, ext = extend || {};
   let url = `${host}/type/${ext.cateId||tid}-${p}.html`;
    
    return JSON.stringify({
        list: getList((await req(url, {headers})).content),
        page: parseInt(p),
        pagecount: parseInt(p) + 1
    });
}
    
async function detail(id) {
    const resp = await req(host + id, { headers });
    const html = resp.content;   
    const playFrom = [], playList = [];
    
    const lines = pdfa(html, '#playListBox .play-list');
    
    lines.forEach((line) => {
        const name = pdfh(line, 'h4 .pull-left&&Text');
        const episodes = pdfa(line, 'ul li a').map(a => 
            pdfh(a, 'a&&Text') + '$' + pdfh(a, 'a&&href')
        ).join('#'); 
        if (name && episodes) {
            playFrom.push(name);
            playList.push(episodes);
        }
    });
    
    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: pdfh(html, 'h2 a&&Text'),
            vod_pic: pdfh(html, 'img&&data-original'),
            vod_year: pdfh(html, 'p:contains(年代) a&&Text'),
            vod_area: pdfh(html, 'p:contains(地区) a&&Text'),
            vod_remarks: pdfh(html, '.text-danger&&Text'),
            type_name: pdfh(html, 'p:contains(类型) a&&Text'),
            vod_actor: pdfa(html, 'p:contains(主演) a').map(it => pdfh(it, 'a&&Text')).map(s => s.trim()).filter(s => s).join('/'),
            vod_director: pdfa(html, 'p:contains(导演) a').map(it => pdfh(it, 'a&&Text')).map(s => s.trim()).filter(s => s).join('/'),
            vod_content: pdfh(html, '.movie-detail&&Text')
                .replace(/^简介：/, '')
                .replace(/Kan影视.*?：/, '')
                .replace(/Kan影视TV.*?www\.kanbook\.cc/, '')
                .trim(),
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playList.join('$$$')
        }]
    });
}


async function search(wd, quick, pg) {
    let p = pg || 1;
    let url = `${host}/search/${wd}-${p}.html`;
    let resp = await req(url, {
        headers
    });
    return JSON.stringify({
        list: getList(resp.content),
        page: parseInt(p),
        pagecount: parseInt(p) + 1
    });
}

async function play(flag, id, flags) {
    try {
        let playUrl = !/^http/.test(id) ? `${host}${id}` : id;
        let resHtml = (await req(playUrl, {
            headers
        })).content;
        let kcode = safeParseJSON(
            resHtml.match(/var\s+player_\w+\s*=\s*(\{[^]*?\})\s*</)?.[1] ?? ''
        );
        let kurl = kcode?.url ?? '';
        let kp = /m3u8|mp4|mkv/i.test(kurl) ? 0 : 1;
        if (kp) kurl = playUrl;
        return JSON.stringify({
            jx: 0,
            parse: kp,
            url: kurl,
            header: headers
        });
    } catch (e) {
        return JSON.stringify({
            jx: 0,
            parse: 0,
            url: '',
            header: {}
        });
    }
}

function safeParseJSON(str) {
    try {
        return JSON.parse(str.trim().replace(/;+$/, ''));
    } catch {
        return null;
    }
}

export default {
    init,
    home,
    homeVod,
    category,
    detail,
    search,
    play
};




