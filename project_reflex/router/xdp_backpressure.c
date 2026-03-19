#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __type(key, __u32);
    __type(value, __u32);
    __uint(max_entries, 128);
} penalty_map SEC(".maps");

static __always_inline int parse_udp(struct xdp_md *ctx, void *data_end)
{
    void *data = (void *)(long)ctx->data;
    struct ethhdr *eth = data;
    struct iphdr *ip;
    struct udphdr *udp;
    __u16 udp_dest;
    __u32 ip_src;

    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    ip = (struct iphdr *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    if (ip->protocol != IPPROTO_UDP)
        return XDP_PASS;

    udp = (struct udphdr *)((void *)ip + sizeof(struct iphdr));
    if ((void *)(udp + 1) > data_end)
        return XDP_PASS;

    udp_dest = bpf_ntohs(udp->dest);
    
    if (udp_dest == 9999) {
        ip_src = bpf_ntohl(ip->saddr);
        
        __u32 penalty = 1;
        bpf_map_update_elem(&penalty_map, &ip_src, &penalty, BPF_ANY);
        
        return XDP_DROP;
    }

    if (udp_dest == 8888) {
        return XDP_PASS;
    }

    return XDP_PASS;
}

SEC("xdp")
int xdp_backpressure(struct xdp_md *ctx)
{
    void *data_end = (void *)(long)ctx->data_end;
    return parse_udp(ctx, data_end);
}

char _license[] SEC("license") = "GPL";
