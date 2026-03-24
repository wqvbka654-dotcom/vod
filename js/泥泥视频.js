var rule = {
    title: "泥泥视频",
    host: "https://www.nivod.vip",
    homeUrl: '/',
    url: '/k/fyfilter/',
    filter_url: '{{fl.cateId}}-{{fl.area}}-------fypage---{{fl.year}}',
    detailUrl: '/nivod/fyid/',
    searchUrl: '/s/**----------fypage---/',
    searchable: 2,
    quickSearch: 1,
    filterable: 1,
    headers: {
        "User-Agent": "MOBILE_UA"
    },
    class_name: '电影&电视剧&综艺&动漫',
    class_url: '1&2&3&4',
    double: false,
    filter_def: {
        1: {
            cateId: '1'
        },
        2: {
            cateId: '2'
        },
        3: {
            cateId: '3'
        },
        4: {
            cateId: '4'
        }
    },
    filter: "H4sIAAAAAAAAA+2W324SQRTGX8XsNRc7u8u/voHPYLjY6F6pvWjUpGlIbAkUaKNiFKXFqol1oWIK0RhhuzwNu8u+hQM7M+fMxGyIkJgm3PV8v52dOdPvO8uBRrSdewfaQ2df29Hu20+cuw+0jLZrP3ZoHY284OKE1s/sR0+d5YO7VA6qvbjSW8i0IFo5w+Rmb+Z3o8YxIzkg7W7QcIHkBYnqo7BSBVIA4raCsQekCG+7PJYI0QUKD1+Fz9sIodM1XGknYsCq+vvZpAHIgBdGk6vAf4uQ1G70Bh3DgH7Do0HUbiEEewW113Gnj5AJezWvI/8KIQteWGmGR2eArCyg76fz+gVCcIzocBqfTRFC9+63Ig/9ryx68aUFTIxg7zk22CDoDoPTSboNoMEvbtypMZUVnMVfO+Hva8ZYIda9HIbjKV+XFOK00xfBuc8YK0T/A5cqjLFCsHeXYXfAWVKIs3zswztZIdb9GAJjhThn9dfMa/NzJgW+un3H3kNXN/458/wVr87QqYe4BZGd7tAqy0DyN1phwQoL6yboJtYN0A2sE9AJ1nXQdaSTotBJEesF0AtYz4Oexzp0THJYz4KO+yXQL8H9EuiX4H4J9LtIfKlcymjGmiMPpfncn01cOlr4UIGtqbepixGysC2RnpUsKXTTVCyOluQkp8IStEV7GPcHCGUVAwNa2GlD0a9V6fM8GkmxStz+dSykxTt1ZKTEe34yAsYKdKlB81Pw4TNfKur/OBzQbNiOhrVHg7nmaDCVMETezbwx4ftAd8l0kGlBMbZMi0qUJGqiibAcFjLVlblAPS8/kFccLNPN/TZIGRDJjfBkJQW6D9o0BH1RpH7/t5G7PZGz1owc7Mu+xs1eePONe5cooZKpoYRKpkXFnBK1/hIq+QGieFSmhhI5mZobi9zyTnjkkmKV72faz+rtV+5WR678B6axA1f1DwAA",
    推荐: "*",
    一级: '.module-poster-items-base a;a&&title;img&&data-original;.module-item-note&&Text;a&&href',
    二级: $js.toString(() => {
        let khtml = request(input);
        VOD = {};
        VOD.vod_id = input;
        VOD.vod_name = pdfh(khtml, 'h1&&Text');
        VOD.type_name = pdfh(khtml, '.module-info-tag-link:eq(2)&&Text');
        VOD.vod_pic = pd(khtml, '.lazyload&&data-original', input);
        VOD.vod_remarks = pdfh(khtml, '.module-info-item:contains(集数)&&Text').replace('集数：', '') || pdfh(khtml, '.module-info-item:contains(备注)&&Text').replace('备注：', '') || pdfh(khtml, '.module-info-item:contains(连载)&&Text').replace('连载：', '');
        VOD.vod_year = pdfh(khtml, '.module-info-tag-link:eq(0)&&Text');
        VOD.vod_area = pdfh(khtml, '.module-info-tag-link:eq(1)&&Text');
        VOD.vod_director = pdfh(khtml, '.module-info-item:contains(导演)&&Text').replace('导演：', '');
        VOD.vod_actor = pdfh(khtml, '.module-info-item:contains(主演)&&Text').replace('主演：', '');
        VOD.vod_content = pdfh(khtml, '.module-info-introduction-content&&Text');
        let ktabs = pdfa(khtml, '.module-tab-items-box .module-tab-item').map((it) => {
            return pdfh(it, '.module-tab-item&&Text').replace(/\s+/g, '').replace(/^(.+?)(\d+)$/, '$1|共$2集')
        });
        VOD.vod_play_from = ktabs.join('$$$');
        let kurls = pdfa(khtml, '.module-play-list').map((pl) => {
            let kurl = pdfa(pl, 'body&&a').map((it) => {
                return pdfh(it, 'a&&Text') + '$' + pd(it, 'a&&href', input)
            });
            return kurl.join('#')
        });
        VOD.vod_play_url = kurls.join('$$$')
    }),
    搜索: '.module-items .module-item;img&&alt;img&&data-original;.module-item-note&&Text;a&&href',
}