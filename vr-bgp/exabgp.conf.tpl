group test {
    process bgpapi {
        run /bgpapi.py;
    }

    process bgprec {
        encoder json;
        receive {
            neighbor-changes;
            parsed;
            update;
        }
        run /bgprec.py;
    }

    router-id {{config.ROUTER_ID}};
    local-as {{config.LOCAL_AS}};

    neighbor {{config.NEIGHBOR}} {
        peer-as {{config.PEER_AS}};
        local-address {{config.LOCAL_ADDRESS}};
    }
}
