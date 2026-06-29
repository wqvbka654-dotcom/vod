/*
title: '金牌app', author: '小可乐/v5.11.1'
*/
import {
    Crypto
} from 'assets://js/lib/cat.js';

var HOST;
const MOBILE_UA = "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36";
const DefHeader = {
    'User-Agent': MOBILE_UA
};
const CachedPlayUrls = {};
const KParams = {
    headers: {
        'User-Agent': MOBILE_UA
    },
    pagecount: 0
};

async function init(cfg) {
    try {
        HOST = cfg.ext?.host?.trim().replace(/\/$/, '') || 'https://m.jiabaide.cn';
        KParams.headers['Referer'] = HOST;
        KParams.catesDeal = cfg.ext?.catesDeal?.trim() || '';
    } catch (e) {
        console.error('初始化参数失败：', e.message);
    }
}

async function home(filter) {
    try {
        let typeUrl = `${HOST}/api/mw-movie/anonymous/get/filer/type`;
        let kres = await request(typeUrl, getHeaders({}));
        if (!kres) {
            throw new Error('请求失败');
        }
        let ktypeObj = JSON.parse(kres)?.data || [];
        let classes = ktypeObj.map(item => {
            return {
                type_name: item.typeName,
                type_id: item.typeId.toString()
            };
        });
        if (KParams.catesDeal) {
            let [x = '', y = '', z = ''] = KParams.catesDeal.split('@');
            let cate_remove = ['', '¥准:'].includes(x.trim()) ? '' : x.trim();
            let cate_order = ['', '#'].includes(y.trim()) ? '' : y.trim();
            let cate_rename = z.trim();
            classes = dorDeal(classes, cate_remove, cate_order, cate_rename);
        }
        let filters = {};
        try {
            let filterUrl = `${HOST}/api/mw-movie/anonymous/v1/get/filer/list`;
            kres = await request(filterUrl, getHeaders({}));
            if (!kres) {
                throw new Error('请求失败');
            }
            let filterObj = JSON.parse(kres)?.data || {};
            let nameObj = {
                typeList: 'type,类型',
                plotList: 'class,剧情',
                districtList: 'area,地区',
                languageList: 'lang,语言',
                yearList: 'year,年份',
                serialList: 'by,排序'
            };
            const byValues = [{
                "n": "最近更新",
                "v": "1"
            }, {
                "n": "添加时间",
                "v": "2"
            }, {
                "n": "人气高低",
                "v": "3"
            }, {
                "n": "评分高低",
                "v": "4"
            }];
            classes.forEach(item => {
                filters[item.type_id] = Object.entries(nameObj).map(([nObjk, nObjv]) => {
                    let [kkey, kname] = nObjv.split(',');
                    let kvalue = (filterObj[item.type_id]?.[nObjk] || []).map(it => {
                        if (nObjk === 'typeList') {
                            return {
                                n: it.itemText,
                                v: it.itemValue
                            };
                        }
                        return {
                            n: it.itemText,
                            v: it.itemText
                        };
                    });
                    kvalue.unshift({
                        "n": "全部",
                        "v": ""
                    });
                    if (nObjk === 'serialList') {
                        kvalue = byValues;
                    }
                    return {
                        key: kkey,
                        name: kname,
                        value: kvalue
                    };
                });
            });
        } catch (e) {}
        return JSON.stringify({
            class: classes,
            filters: filters
        });
    } catch (e) {
        console.error('首页获取分类失败：', e.message);
        return JSON.stringify({
            class: [],
            filters: {}
        });
    }
}

async function homeVod() {
    try {
        let homeUrl = `${HOST}/api/mw-movie/anonymous/home/hotSearch`;
        let kres = await request(homeUrl, getHeaders({}));
        if (!kres) {
            throw new Error('请求失败');
        }
        let udVods = JSON.parse(kres)?.data || [];
        let VODS = getVodList(udVods);
        return JSON.stringify({
            list: VODS
        });
    } catch (e) {
        console.error('推荐页获取失败：', e.message);
        return JSON.stringify({
            list: []
        });
    }
}

async function category(tid, pg, filter, extend) {
    try {
        let pgParse = parseInt(pg, 10);
        pg = pgParse < 1 || isNaN(pgParse) ? 1 : pgParse;
        let cateBody = {
            area: extend?.area || '',
            lang: extend?.lang || '',
            pageNum: pg.toString(),
            pageSize: '30',
            sort: extend?.by || '1',
            sortBy: '1',
            type: extend?.type || '',
            type1: tid,
            v_class: extend?.class || '',
            year: extend?.year || '',
        };
        let cateUrl = `${HOST}/api/mw-movie/anonymous/video/list?${objToForm(cateBody)}`;
        let kres = await request(cateUrl, getHeaders(cateBody));
        if (!kres) {
            throw new Error('请求失败');
        }
        let udVods = JSON.parse(kres)?.data?.list || [];
        let VODS = getVodList(udVods);
        let pgCountParse = parseInt(KParams.pagecount, 10);
        let pagecount = pgCountParse < 1 || isNaN(pgCountParse) ? 999 : pgCountParse;
        return JSON.stringify({
            list: VODS,
            page: pg,
            pagecount: pagecount,
            limit: 30,
            total: 30 * pagecount
        });
    } catch (e) {
        console.error('分类页获取失败：', e.message);
        return JSON.stringify({
            list: [],
            page: 1,
            pagecount: 0,
            limit: 1,
            total: 0
        });
    }
}

async function search(wd, quick, pg) {
    try {
        let pgParse = parseInt(pg, 10);
        pg = pgParse < 1 || isNaN(pgParse) ? 1 : pgParse;
        let searchBody = {
            keyword: wd,
            pageNum: pg.toString(),
            pageSize: '30',
        };
        let searchUrl = `${HOST}/api/mw-movie/anonymous/video/searchByWordPageable?${objToForm(searchBody)}`;
        let kres = await request(searchUrl, getHeaders(searchBody));
        if (!kres) {
            throw new Error('请求失败');
        }
        let udVods = JSON.parse(kres)?.data?.list || [];
        let VODS = getVodList(udVods);
        return JSON.stringify({
            list: VODS,
            page: pg,
            pagecount: 10,
            limit: 30,
            total: 300
        });
    } catch (e) {
        console.error('搜索页获取失败：', e.message);
        return JSON.stringify({
            list: [],
            page: 1,
            pagecount: 0,
            limit: 30,
            total: 0
        });
    }
}

async function detail(id) {
    try {
        let detailBody = {
            id: id
        };
        let detailUrl = `${HOST}/api/mw-movie/anonymous/video/detail?${objToForm(detailBody)}`;
        let kres = await request(detailUrl, getHeaders(detailBody));
        if (!kres) {
            throw new Error('请求失败');
        }
        let kdetailObj = JSON.parse(kres);
        let kvod = kdetailObj?.data || '';
        if (!kvod) {
            throw new Error('kvod解析失败');
        }
        let kid = kvod.vodId;
        let kurls = (kvod.episodeList || []).map((it) => {
            return `${it.name}$${kid}@${it.nid}`
        }).join('#');
        let VOD = {
            vod_id: kid,
            vod_name: kvod.vodName,
            vod_pic: kvod.vodPic,
            type_name: kvod.vodClass || '类型',
            vod_remarks: kvod.vodRemarks || '状态',
            vod_year: kvod.vodYear || '0000',
            vod_area: kvod.vodArea || '年份',
            vod_lang: kvod.vodLang || '地区',
            vod_director: kvod.vodDirector || '导演',
            vod_actor: kvod.vodActor || '主演',
            vod_content: kvod.vodContent || '简介',
            vod_play_from: '天扬影视',
            vod_play_url: kurls
        };
        return JSON.stringify({
            list: [VOD]
        });
    } catch (e) {
        console.error('详情页获取失败：', e.message);
        return JSON.stringify({
            list: []
        });
    }
}

async function play(flag, id, flags) {
    try {
        if (CachedPlayUrls[id]) {
            return CachedPlayUrls[id];
        }
        let [sid, nid] = id.match(/\d+/g);
        let parseBody = {
            clientType: '3',
            id: sid,
            nid: nid,
        };
        let parseUrl = `${HOST}/api/mw-movie/anonymous/v2/video/episode/url?${objToForm(parseBody)}`;
        let kres = await request(parseUrl, getHeaders(parseBody));
        if (!kres) {
            kres = '{}';
        }
        let parseObj = JSON.parse(kres);
        let kurl = [];
        (parseObj?.data?.list || []).forEach((it) => {
            kurl.push(it.resolutionName, it.url);
        });
        let playObj = {
            jx: 0,
            parse: 0,
            url: kurl,
            header: DefHeader
        };
        let playJson = JSON.stringify(playObj);
        if (playObj.url !== []) {
            CachedPlayUrls[id] = playJson
        };
        return playJson;
    } catch (e) {
        console.error('播放失败：', e.message);
        return JSON.stringify({
            jx: 0,
            parse: 0,
            url: '',
            header: {}
        });
    }
}

function objToForm(obj) {
    return Object.entries(obj).map(([k, v]) => `${k}=${v}`).join('&');
}

function getHeaders(obj) {
    try {
        let t = Date.now().toString();
        obj.key = 'cb808529bae6b6be45ecfab29a4889bc';
        obj.t = t;
        let objStr = objToForm(obj);
        let sign = Crypto.SHA1(Crypto.MD5(objStr).toString()).toString();
        return {
            ...KParams.headers,
            t: t,
            sign: sign
        };
    } catch (e) {
        return {};
    }
}

function dorDeal(kArr, strRemove, strOrder, strRename) {
    let dealed_arr = kArr;
    if (strRemove) {
        try {
            let filtered_arr;
            if (/^¥准:/.test(strRemove)) {
                let removeArr = strRemove.split(',');
                const removeSet = new Set(removeArr);
                filtered_arr = dealed_arr.filter(it => !removeSet.has(it.type_name));
            } else {
                let removeStr = strRemove.replace(/,/g, '|');
                let removeReg = new RegExp(removeStr);
                filtered_arr = dealed_arr.filter(it => !removeReg.test(it.type_name));
            }
            let retained_arr = filtered_arr.length ? filtered_arr : [dealed_arr[0]];
            dealed_arr = retained_arr;
        } catch (e) {
            console.error('删除失败：', e);
        }
    }
    if (strOrder) {
        try {
            let [a = '', b = ''] = strOrder.split('#', 2);
            let arrA = a.split('>').filter(it => it !== '');
            let arrB = b.split('<').filter(it => it !== '');
            let uqArrB = arrB.filter(it => !arrA.includes(it));
            let twMap = new Map();
            arrA.forEach((item, idx) => {
                twMap.set(item, {
                    weight: 1,
                    index: idx
                });
            });
            uqArrB.forEach((item, idx) => {
                twMap.set(item, {
                    weight: 3,
                    index: idx
                });
            });
            dealed_arr.forEach((it, idx) => {
                if (!twMap.has(it.type_name)) {
                    twMap.set(it.type_name, {
                        weight: 2,
                        index: idx
                    });
                }
            });
            let ordered_arr = [...dealed_arr].sort((a, b) => {
                let {
                    weight: ta = 2,
                    index: idxA = 0
                } = twMap.get(a.type_name) ?? {};
                let {
                    weight: tb = 2,
                    index: idxB = 0
                } = twMap.get(b.type_name) ?? {};
                if (ta !== tb) return ta - tb;
                return ta === 3 ? idxB - idxA : idxA - idxB;
            });
            dealed_arr = ordered_arr;
        } catch (e) {
            console.error('排序失败：', e);
        }
    }
    if (strRename) {
        try {
            const objRename = {};
            for (let p of strRename.split('&')) {
                let [k, v] = p.split('>>', 2);
                (k ?? '') + (v ?? '') && (objRename[k ?? ''] = v ?? '');
            }
            let renamed_arr = dealed_arr.map(it => {
                return {
                    ...it,
                    type_name: objRename[it.type_name] || it.type_name
                }
            });
            dealed_arr = renamed_arr;
        } catch (e) {
            console.error('改名失败：', e);
        }
    }
    return dealed_arr;
}

function getVodList(vods) {
    try {
        if (!Array.isArray(vods)) {
            throw new Error();
        }
        let fvods = [];
        vods.forEach((it) => {
            fvods.push({
                vod_name: it.vodName,
                vod_pic: it.vodPic,
                vod_remarks: `${it.vodRemarks}_${it.vodDoubanScore}`,
                vod_year: it.vodPubdate.split('-')[0],
                vod_id: it.vodId
            })
        });
        return fvods;
    } catch (e) {
        return vods;
    }
}

async function request(reqUrl, header, method, data, dataType) {
    if (!reqUrl || typeof reqUrl !== 'string') {
        console.error('reqUrl 不能为空且必须是字符串');
        return '';
    }
    if (typeof header !== 'object' || header === null) {
        header = KParams.headers;
    } else if (Object.keys(header).length === 0) {
        header = KParams.headers;
    }
    try {
        let optObj = {
            headers: header,
            method: method?.toLowerCase() || 'get',
            timeout: KParams.timeout || 5000,
        };
        if (method === 'post') {
            optObj.data = data ?? '';
            optObj.postType = dataType?.toLowerCase() || 'form';
        }
        let res = await req(reqUrl, optObj);
        if (res === null || res === undefined || res.content === undefined) {
            console.warn('未找到 content 字段', res);
            return '';
        }
        return res.content;
    } catch (e) {
        console.error(`${method} 请求失败：`);
        return '';
    }
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        search: search,
        detail: detail,
        play: play,
        proxy: null
    };
}