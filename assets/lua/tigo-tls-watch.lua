-- Tigo: notice servers that reject a desynced TLS handshake.
--
-- When a strategy's fake or seqovl part reaches the server, the server answers
-- the broken ClientHello with a plaintext fatal TLS alert (record 15 03 xx 00 02 02)
-- and the browser shows ERR_SSL_PROTOCOL_ERROR. winws2 intercepts only such
-- inbound packets (--wf-raw-part), so this runs on a handful of packets.
--
-- tigo_tls_watch sits first in every profile and appends one line per server
-- to tls-alerts.txt in the --writable directory:
--   d <hostname> <ip> <alert>   the profile excludes by hostlist-exclude
--   i - <ip> <alert>            the profile excludes by ipset only (arg exclude=ip)
-- The Tigo daemon moves those into the user's exclude lists; winws2 rereads
-- list files on change. Requires zapret-lib.lua (host_ip, writable_file_name).

local tigo_reported = {}

local function tigo_is_fatal_alert(payload)
	return payload and #payload >= 7
		and string.byte(payload, 1) == 0x15 -- alert record
		and string.byte(payload, 2) == 0x03 -- TLS version major
		and string.byte(payload, 4) == 0x00 and string.byte(payload, 5) == 0x02 -- plaintext, 2 bytes
		and string.byte(payload, 6) == 0x02 -- level: fatal
end

function tigo_tls_watch(ctx, desync)
	if desync.outgoing then return end
	local payload = desync.dis.payload
	if not tigo_is_fatal_alert(payload) then return end

	local ip = host_ip(desync)
	local track = desync.track
	local host = track and not track.hostname_is_ip and track.hostname or nil
	local entry
	if host and desync.arg.exclude ~= "ip" then
		entry = "d " .. host .. " " .. (ip or "-")
	elseif ip then
		entry = "i - " .. ip
	else
		return
	end
	if tigo_reported[entry] then return end
	tigo_reported[entry] = true

	local f = io.open(writable_file_name("tls-alerts.txt"), "a")
	if f then
		f:write(entry .. " " .. string.byte(payload, 7) .. "\n")
		f:close()
	end
	DLOG("tigo_tls_watch: fatal TLS alert " .. string.byte(payload, 7) .. ": " .. entry)
end
