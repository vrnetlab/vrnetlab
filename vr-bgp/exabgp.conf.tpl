process bgpapi {
    encoder json;
    run /bgpapi.py;
}

process bgprec {
    encoder json;
    run /bgprec.py;
}

template test {
    neighbor test {
        router-id {{config.ROUTER_ID}};
        local-as {{config.LOCAL_AS}};
        api connection {
            processes [ bgprec ];
            neighbor-changes;
            receive {
                parsed;
                update;
            }
        }
        {%- if config.ROUTEREFRESH %}
        capability {
            route-refresh;
        }
        {%- endif %}
    }
}

{%- if config.IPV4_NEIGHBOR %}
neighbor {{config.IPV4_NEIGHBOR}} {
    inherit test;
    peer-as {{config.PEER_AS}};
    local-address {{config.IPV4_LOCAL_ADDRESS}};
    {%- if not config.ALLOW_MIXED_AFI_TRANSPORT %}
    family {
        ipv4 unicast;
    }
    {%- endif %}
    {%- if config.MD5 %}
    md5 "{{config.MD5}}";
    {%- endif %}
    {%- if config.LISTEN %}
    listen 179;
    {%- endif %}
    {%- if config.TTLSECURITY %}
    ttl-security;
    {%- endif %}
}
{%- endif %}
{%- if config.IPV6_NEIGHBOR %}
neighbor {{config.IPV6_NEIGHBOR}} {
    inherit test;
    peer-as {{config.PEER_AS}};
    local-address {{config.IPV6_LOCAL_ADDRESS}};
    {%- if not config.ALLOW_MIXED_AFI_TRANSPORT %}
    family {
        ipv6 unicast;
    }
    {%- endif %}
    {%- if config.MD5 %}
    md5 "{{config.MD5}}";
    {%- endif %}
    {%- if config.LISTEN %}
    listen 179;
    {%- endif %}
    {%- if config.TTLSECURITY %}
    ttl-security;
    {%- endif %}
}
{%- endif %}
