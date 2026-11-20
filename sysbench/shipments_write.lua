-- W1 uses uniform sender IDs, as allowed by the study protocol.
sysbench.cmdline.options = {
    mode = {"insert or update", "insert"},
    table_name = {"Target shipments table", "shipments"},
    max_id = {"Largest contiguous baseline ID", 1000000},
    start_id = {"First sequence number for new tracking codes", 1},
    batch = {"Writes per transaction (1 or 100)", 1}
}

local con, seq
function thread_init()
    assert(sysbench.opt.table_name:match("^[_%a][_%w]*$"))
    assert(sysbench.opt.mode == "insert" or sysbench.opt.mode == "update")
    assert(sysbench.opt.batch == 1 or sysbench.opt.batch == 100)
    con = sysbench.sql.driver():connect()
    seq = sysbench.opt.start_id + sysbench.tid
end

function thread_done()
    con:disconnect()
end

local function insert_order()
    -- Disjoint per-thread sequences, spread over the odd 12-digit codes.
    local serial = ((seq * 104729) % 500000000000) * 2 + 1
    seq = seq + sysbench.opt.threads
    local rand = sysbench.rand.uniform
    local r = rand(1, 100)
    local status = (r <= 3 and 1) or (r <= 7 and 2) or (r <= 12 and 3)
        or (r <= 17 and 4) or (r <= 97 and 5) or 6
    con:query(string.format(
        "INSERT INTO %s (tracking_code,sender_id,origin_hub_id,dest_hub_id,status," ..
        "cod_amount,weight_grams,shipping_fee,recipient_phone,recipient_address,note,created_at,updated_at) " ..
        "VALUES ('VN%012d',%d,%d,%d,%d,%d,%d,%d,'09%08d','%d duong Nguyen Trai, phuong Trung Van, quan Nam Tu Liem, Ha Noi',%s,NOW(),NOW())",
        sysbench.opt.table_name, serial, rand(1,100000), rand(1,200), rand(1,200),
        status, rand(0,9999999), rand(100,10000), rand(15000,150000), rand(0,99999999),
        rand(1,999), rand(1,100) <= 60 and "'Giao trong gio hanh chinh'" or "NULL"))
end

function event()
    if sysbench.opt.batch > 1 then con:query("BEGIN") end
    for i = 1, sysbench.opt.batch do
        if sysbench.opt.mode == "insert" then
            insert_order()
        else
            con:query(string.format("UPDATE %s SET status=%d, updated_at=NOW() WHERE id=%d",
                sysbench.opt.table_name, sysbench.rand.uniform(1,6),
                sysbench.rand.uniform(1,sysbench.opt.max_id)))
        end
    end
    if sysbench.opt.batch > 1 then con:query("COMMIT") end
end
