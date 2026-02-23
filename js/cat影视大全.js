let host = 'https://www.iysdq.com';
let headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2102J2SC Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/144.0.7559.31 Mobile Safari/537.36',
};

function getList(html) {
    let videos = [];
    let selector = '';
    if (html.includes('class="public-list-box')) selector = '.public-list-box';
    else if (html.includes('class="public-list-box')) selector = '.public-list-box';
    if (!selector) return videos;
    const items = pdfa(html, selector);
    items.forEach(it => {
        const id = pdfh(it, 'a&&href');
        const name = pdfh(it, 'a&&title');
        const pic = pdfh(it, 'img&&data-src');
        const remark = pdfh(it, '.ft2&&Text');
        videos.push({
            vod_id: id,
            vod_name: name,
            vod_pic: pic,
            vod_remarks: remark
        });
    });
    return videos;
}

// 中文名转key
function filterNameToKey(name) {
    const map = {
        '类型': 'class_',
        '剧情': 'class_',
        '地区': 'area',
        '年份': 'year',
        '语言': 'lang',
        '字母': 'letter',
        '排序': 'by'
    };
    return map[name] || name;
}

// 提取单个分类的筛选器
async function extractFiltersForCategory(cateId) {
    const filters = [];
    const filterUrl = `${host}/vodshow/${cateId}-----------.html`;
    
    try {
        const filterResp = await req(filterUrl, { headers });
        const filterHtml = filterResp.content;
        
        // 提取各个筛选维度
        const filterSections = pdfa(filterHtml, '.ec-casc-list .nav-swiper');
        
        filterSections.forEach(section => {
            const title = pdfh(section, '.filter-text span&&Text');
            if (!title || title === '已选' || title === '频道') return;
            
            const key = filterNameToKey(title);
            const values = [];
            
            const optionItems = pdfa(section, 'ul.swiper-wrapper li');
            optionItems.forEach(li => {
                const text = pdfh(li, 'a&&Text');
                
                // 筛选值规则："全部"对应空字符串，其他对应文本值
                const value = text.trim() === '全部' ? '' : text.trim();
                
                values.push({
                    n: text.trim(),
                    v: value
                });
            });
            
            if (values.length > 0 && key) {
                filters.push({
                    key: key,
                    name: title,
                    value: values
                });
            }
        });
        
        // 添加排序筛选器(固定)
        filters.push({
            key: 'by',
            name: '排序',
            value: [
                {n: '时间', v: 'time'},
                {n: '人气', v: 'hits'},
                {n: '评分', v: 'score'}
            ]
        });
        
    } catch (e) {
        console.log(`提取分类${cateId}筛选器失败: ${e.message}`);
    }
    
    return filters;
}

async function init(cfg) {}

async function home(filter) {
    // 1. 实时提取分类(class)
    const homeResp = await req(host, { headers });
    const homeHtml = homeResp.content;
    
    const classItems = [];
    const navItems = pdfa(homeHtml, '.this-wap.roll ul.swiper-wrapper li');
    navItems.forEach(item => {
        const href = pdfh(item, 'a&&href');
        const name = pdfh(item, 'a&&Text');
        // 只提取/vodtype/开头的链接
        const match = href.match(/\/vodtype\/(\d+)\.html/);
        if (match) {
            classItems.push({
                type_id: match[1],
                type_name: name.trim()
            });
        }
    });
    
    // 2. 为每个分类单独提取筛选器
    const filters = {};
    
    // 使用Promise.all并行请求所有分类的筛选器
    const filterPromises = classItems.map(async (cate) => {
        const cateFilters = await extractFiltersForCategory(cate.type_id);
        return { type_id: cate.type_id, filters: cateFilters };
    });
    
    const results = await Promise.all(filterPromises);
    
    results.forEach(result => {
        filters[result.type_id] = result.filters;
    });
    
    return JSON.stringify({
        class: classItems,
        filters: filters
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
    const p = pg || 1;
    const cateId = extend.cateId || tid;
    const class_ = extend.class_ || '';
    const area = extend.area || '';
    const lang = extend.lang || '';
    const letter = extend.letter || '';
    const year = extend.year || '';
    const by = extend.by || '';

    const url = `${host}/vodshow/${cateId}-${area}-${by}-${class_}-${lang}-${letter}---${p}---${year}.html`;

    const resp = await req(url, {
        headers
    });
    return JSON.stringify({
        list: getList(resp.content),
        page: parseInt(p),
        pagecount: parseInt(p) + 1
    });
}

async function detail(id) {
    const url = host + id;
    const resp = await req(url, {
        headers
    });
    const html = resp.content;
    const blockList = ["http下载"];
    const tabs = pdfa(html, 'a.swiper-slide');
    const lists = pdfa(html, '.anthology-list-box ul');
    const playPairs = tabs
        .map((tab, idx) => {
            const name = pdfh(tab, 'a&&Text').replace(/\s+/g, '').replace(/(\D+)(\d+)/, '$1|共$2集');
            const urlArr = pdfa(lists[idx] || '', 'a')
                .map(a => pdfh(a, 'a&&Text') + '$' + pdfh(a, 'a&&href'))
                .join('#');
            return {
                name,
                url: urlArr
            };
        })
        .filter(item => !blockList.some(block => item.name.includes(block)));
    const playFrom = playPairs.map(p => p.name).join('$$$');
    const playUrl = playPairs.map(p => p.url).join('$$$');
    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: pdfh(html, '.this-desc-title&&Text'),
            vod_pic: pdfh(html, '.this-pic-bj&&style'),
            vod_year: pdfh(html, '.slide-desc-box&&span:eq(3)&&Text'),
            vod_area: pdfh(html, '.slide-desc-box&&span:eq(4)&&Text'),
            vod_remarks: pdfh(html, '.slide-desc-box&&span:eq(5)&&Text'),
            type_name: pdfa(html, '.this-desc-tags&&span').map((it) => pdfh(it, 'body&&Text')).join('/'),
            vod_actor: pdfa(html, '.this-info:contains(演员) a').map(it => pdfh(it, 'body&&Text')).join('/'),
            vod_director: pdfa(html, '.this-info:contains(导演) a').map(it => pdfh(it, 'body&&Text')).join('/'),
            vod_content: pdfh(html, '.text&&Text').replace(/\s+/g, '').replace("描述:", ""),
            vod_play_from: playFrom,
            vod_play_url: playUrl
        }]
    });
}

async function search(wd, quick, pg) {
    let p = pg || 1;
    let url = `${host}/vodsearch/${wd}----------${p}---.html`;
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
