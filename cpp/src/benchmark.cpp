#include <iostream>
#include <vector>
#include <string>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cmath>
#include <random>
#include <chrono>
#include <algorithm>
#include <numeric>
#include <map>
#include <functional>
using namespace std;

/* ============================================================
 * 1. 自包含 SHA-256 实现（公共领域标准实现）
 * ============================================================ */
namespace sha256 {
    inline uint32_t rotr(uint32_t x, uint32_t n) { return (x >> n) | (x << (32 - n)); }
    inline uint32_t ch(uint32_t x, uint32_t y, uint32_t z) { return (x & y) ^ (~x & z); }
    inline uint32_t maj(uint32_t x, uint32_t y, uint32_t z) { return (x & y) ^ (x & z) ^ (y & z); }
    inline uint32_t ep0(uint32_t x) { return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22); }
    inline uint32_t ep1(uint32_t x) { return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25); }
    inline uint32_t sig0(uint32_t x) { return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3); }
    inline uint32_t sig1(uint32_t x) { return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10); }

    static const uint32_t K[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };

    struct Context {
        uint8_t data[64];
        uint32_t datalen = 0;
        uint64_t bitlen = 0;
        uint32_t state[8];
        Context() {
            state[0]=0x6a09e667; state[1]=0xbb67ae85; state[2]=0x3c6ef372; state[3]=0xa54ff53a;
            state[4]=0x510e527f; state[5]=0x9b05688c; state[6]=0x1f83d9ab; state[7]=0x5be0cd19;
        }
        void transform(const uint8_t* data) {
            uint32_t a,b,c,d,e,f,g,h,t1,t2,m[64];
            for (int i=0,j=0; i<16; ++i, j+=4)
                m[i] = (data[j]<<24)|(data[j+1]<<16)|(data[j+2]<<8)|(data[j+3]);
            for (int i=16; i<64; ++i)
                m[i] = sig1(m[i-2]) + m[i-7] + sig0(m[i-15]) + m[i-16];
            a=state[0]; b=state[1]; c=state[2]; d=state[3];
            e=state[4]; f=state[5]; g=state[6]; h=state[7];
            for (int i=0; i<64; ++i) {
                t1 = h + ep1(e) + ch(e,f,g) + K[i] + m[i];
                t2 = ep0(a) + maj(a,b,c);
                h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
            }
            state[0]+=a; state[1]+=b; state[2]+=c; state[3]+=d;
            state[4]+=e; state[5]+=f; state[6]+=g; state[7]+=h;
        }
        void update(const uint8_t* d, size_t len) {
            for (size_t i=0; i<len; ++i) {
                data[datalen++] = d[i];
                if (datalen == 64) { transform(data); bitlen += 512; datalen = 0; }
            }
        }
        void final(uint8_t hash[32]) {
            uint32_t i = datalen;
            if (datalen < 56) {
                data[i++] = 0x80;
                while (i < 56) data[i++] = 0x00;
            } else {
                data[i++] = 0x80;
                while (i < 64) data[i++] = 0x00;
                transform(data);
                memset(data, 0, 56);
            }
            bitlen += datalen * 8;
            data[63] = bitlen; data[62] = bitlen >> 8; data[61] = bitlen >> 16; data[60] = bitlen >> 24;
            data[59] = bitlen >> 32; data[58] = bitlen >> 40; data[57] = bitlen >> 48; data[56] = bitlen >> 56;
            transform(data);
            for (i=0; i<4; ++i) {
                hash[i]    = (state[0] >> (24-i*8)) & 0xff;
                hash[i+4]  = (state[1] >> (24-i*8)) & 0xff;
                hash[i+8]  = (state[2] >> (24-i*8)) & 0xff;
                hash[i+12] = (state[3] >> (24-i*8)) & 0xff;
                hash[i+16] = (state[4] >> (24-i*8)) & 0xff;
                hash[i+20] = (state[5] >> (24-i*8)) & 0xff;
                hash[i+24] = (state[6] >> (24-i*8)) & 0xff;
                hash[i+28] = (state[7] >> (24-i*8)) & 0xff;
            }
        }
    };

    string hash(const string& str) {
        Context ctx;
        ctx.update((const uint8_t*)str.data(), str.size());
        uint8_t h[32];
        ctx.final(h);
        string out(64, '0');
        const char* hex = "0123456789abcdef";
        for (int i=0; i<32; ++i) {
            out[i*2]   = hex[h[i] >> 4];
            out[i*2+1] = hex[h[i] & 0xf];
        }
        return out;
    }
}

/* ============================================================
 * 2. 公共辅助函数
 * ============================================================ */
inline string H(const vector<string>& parts) {
    string all;
    for (auto& p : parts) all += p;
    return sha256::hash(all);
}

string gen_payload(mt19937& rng, int len = 100) {
    const char alphanum[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    string s(len, '0');
    for (int i=0; i<len; ++i) s[i] = alphanum[rng() % (sizeof(alphanum)-1)];
    return s;
}

// 防止编译器优化掉更新操作
string g_sink;

/* ============================================================
 * 3. BHDS（三域解耦，O(1) 本地更新，不含全局 Merkle 根）
 * ============================================================ */
class BHDS {
public:
    struct Node {
        uint64_t id;
        uint64_t version;
        string data;
        string h; // 独立哈希域
        string p; // 前驱指针域
    };
    vector<Node> nodes; // 按 id 有序存储，id 即索引

    void init(int n, const vector<string>& payloads) {
        nodes.resize(n);
        for (int i = 0; i < n; ++i) {
            nodes[i].id = i;
            nodes[i].version = 0;
            nodes[i].data = payloads[i];
            nodes[i].h = H({"D", to_string(i), "0", payloads[i]});
            if (i == 0) nodes[i].p = H({"P", "0", "0"});
            else        nodes[i].p = H({"P", to_string(i-1), nodes[i-1].h});
        }
    }

    // 仅执行 O(1) 本地字段更新：当前节点 + 直接后继指针
    // 返回当前节点新哈希，用于防优化
    const string& update(int idx, const string& new_data) {
        Node& cur = nodes[idx];
        cur.version++;
        cur.data = new_data;
        cur.h = H({"D", to_string(cur.id), to_string(cur.version), cur.data});

        // 直接后继：实验场景中 id 连续，故为 idx+1
        if (idx + 1 < (int)nodes.size()) {
            Node& suc = nodes[idx + 1];
            suc.p = H({"P", to_string(cur.id), cur.h});
        }
        return cur.h;
    }
};

/* ============================================================
 * 4. 传统哈希链（级联 O(n) 更新）
 * ============================================================ */
class HashChain {
public:
    struct Node {
        string data;
        string hash; // 级联哈希，嵌套前驱
    };
    vector<Node> chain;

    void init(int n, const vector<string>& payloads) {
        chain.resize(n);
        for (int i = 0; i < n; ++i) {
            chain[i].data = payloads[i];
            if (i == 0) chain[i].hash = H({"CHAIN", "0", payloads[i]});
            else        chain[i].hash = H({"CHAIN", chain[i-1].hash, payloads[i]});
        }
    }

    // 从 idx 开始重算到链尾，O(n)
    const string& update(int idx, const string& new_data) {
        chain[idx].data = new_data;
        for (int i = idx; i < (int)chain.size(); ++i) {
            if (i == 0) chain[i].hash = H({"CHAIN", "0", chain[i].data});
            else        chain[i].hash = H({"CHAIN", chain[i-1].hash, chain[i].data});
        }
        return chain.back().hash;
    }
};

/* ============================================================
 * 5. 标准 Merkle 树（数组实现，O(log n) 路径更新）
 * ============================================================ */
class StdMerkleTree {
public:
    int n = 0, offset = 1;
    vector<string> tree; // 1-based，内部节点 + 叶子

    void init(int n_, const vector<string>& payloads) {
        n = n_;
        offset = 1;
        while (offset < n) offset <<= 1;
        tree.assign(2 * offset, "");
        // 叶子
        for (int i = 0; i < n; ++i) tree[offset + i] = H({"LEAF", to_string(i), payloads[i]});
        for (int i = n; i < offset; ++i) tree[offset + i] = H({"LEAF", to_string(i), ""});
        // 内部节点
        for (int i = offset - 1; i >= 1; --i) tree[i] = H({"NODE", tree[i<<1], tree[i<<1|1]});
    }

    // 更新叶子并沿路径重算到根，O(log n)
    const string& update(int idx, const string& new_data) {
        int pos = offset + idx;
        tree[pos] = H({"LEAF", to_string(idx), new_data});
        pos >>= 1;
        while (pos >= 1) {
            tree[pos] = H({"NODE", tree[pos<<1], tree[pos<<1|1]});
            pos >>= 1;
        }
        return tree[1];
    }
};

/* ============================================================
 * 6. 微基准测试框架
 * ============================================================ */
struct Result {
    double mean_ns = 0;
    double std_ns = 0;
};

template<typename UpdateFunc>
Result benchmark(UpdateFunc&& update_fn, int warmup, int iterations, mt19937& rng, int n) {
    g_sink.reserve((warmup + iterations) * 80);
    // 预热
    for (int i = 0; i < warmup; ++i) {
        int idx = rng() % n;
        g_sink += update_fn(idx, gen_payload(rng));
    }

    vector<long long> times;
    times.reserve(iterations);
    for (int i = 0; i < iterations; ++i) {
        int idx = rng() % n;
        string payload = gen_payload(rng);
        auto t1 = chrono::high_resolution_clock::now();
        g_sink += update_fn(idx, payload);
        auto t2 = chrono::high_resolution_clock::now();
        times.push_back(chrono::duration_cast<chrono::nanoseconds>(t2 - t1).count());
    }

    Result r;
    double sum = 0;
    for (auto v : times) sum += v;
    r.mean_ns = sum / times.size();
    double sq = 0;
    for (auto v : times) sq += (v - r.mean_ns) * (v - r.mean_ns);
    r.std_ns = sqrt(sq / times.size());
    return r;
}

struct PerScaleMeans {
    double bhds, chain, merkle;
};

// 对5个值排序，去掉最低/最高，返回中间3个的均值与样本标准差
static pair<double,double> trimmed_mean_std(vector<double> v) {
    sort(v.begin(), v.end());                 // 升序
    // 20% trim: 5个值去掉1个最低、1个最高，剩中间3个
    vector<double> m(v.begin() + 1, v.end() - 1);
    double sum = accumulate(m.begin(), m.end(), 0.0);
    double mean = sum / m.size();             // 3个值的均值
    double sq = 0.0;
    for (double x : m) sq += (x - mean) * (x - mean);
    double std = sqrt(sq / m.size());         // 这3个值的标准差
    return {mean, std};
}

int main() {
    const vector<int> scales = {1000, 10000, 50000, 100000, 200000};
    const int WARMUP = 200;
    const int ITERATIONS = 2000;
    const int PAYLOAD_SIZE = 100;
    const vector<uint32_t> seeds = {20241114, 20241115, 20241116, 20241117, 20241118};

    printf("C++17 BHDS Cross-Language Validation (Table 8)\n");
    printf("5 independent runs, 20%% trimmed mean over per-run means\n");
    printf("Warmup=%d, Iterations=%d, Payload=%d bytes\n\n", WARMUP, ITERATIONS, PAYLOAD_SIZE);

    // 收集结果: scale -> vector of 5 run means
    map<int, vector<PerScaleMeans>> raw;

    for (uint32_t seed : seeds) {
        printf("--- Seed %u ---\n", seed);
        printf("%-10s %-18s %-18s %-18s\n", "Scale", "BHDS(ns)", "Chain(ns)", "Merkle(ns)");

        for (int n : scales) {
            // 每轮用当前 seed + n 的偏移保证不同规模也独立
            mt19937 rng_payload(seed ^ static_cast<uint32_t>(n));
            vector<string> payloads(n);
            for (int i = 0; i < n; ++i) payloads[i] = gen_payload(rng_payload, PAYLOAD_SIZE);

            BHDS bhds;        bhds.init(n, payloads);
            HashChain chain;  chain.init(n, payloads);
            StdMerkleTree mt; mt.init(n, payloads);

            mt19937 rng_bhds(seed ^ 0xA0000001u ^ static_cast<uint32_t>(n));
            mt19937 rng_chain(seed ^ 0xB0000002u ^ static_cast<uint32_t>(n));
            mt19937 rng_merkle(seed ^ 0xC0000003u ^ static_cast<uint32_t>(n));

            auto r_bhds   = benchmark([&](int idx, const string& d){ return bhds.update(idx, d); },
                                      WARMUP, ITERATIONS, rng_bhds, n);
            auto r_chain  = benchmark([&](int idx, const string& d){ return chain.update(idx, d); },
                                      WARMUP, ITERATIONS, rng_chain, n);
            auto r_merkle = benchmark([&](int idx, const string& d){ return mt.update(idx, d); },
                                      WARMUP, ITERATIONS, rng_merkle, n);

            raw[n].push_back({r_bhds.mean_ns, r_chain.mean_ns, r_merkle.mean_ns});

            printf("%-10d %-18.1f %-18.1f %-18.1f\n",
                   n, r_bhds.mean_ns, r_chain.mean_ns, r_merkle.mean_ns);
        }
        printf("\n");
    }

    printf("================================================================================\n");
    printf("FINAL: 20%% Trimmed Mean +/- StdDev (3 middle runs)\n");
    printf("%-10s %-22s %-22s %-22s\n", "Scale", "BHDS(ns)", "Chain(ns)", "Merkle(ns)");
    printf("--------------------------------------------------------------------------------\n");

    for (int n : scales) {
        vector<double> v_bhds, v_chain, v_merkle;
        for (auto& p : raw[n]) {
            v_bhds.push_back(p.bhds);
            v_chain.push_back(p.chain);
            v_merkle.push_back(p.merkle);
        }
        auto s_b   = trimmed_mean_std(v_bhds);
        auto s_c   = trimmed_mean_std(v_chain);
        auto s_m   = trimmed_mean_std(v_merkle);

        printf("%-10d %-22.1f %-22.1f %-22.1f\n",
               n, s_b.first, s_c.first, s_m.first);
        printf("%-10s %-22.1f %-22.1f %-22.1f\n",
               "", s_b.second, s_c.second, s_m.second);
    }

    printf("\nNote: BHDS measures local field update only (excludes global root recomputation).\n");
    printf("      HashChain measures full cascaded recalculation (O(n)).\n");
    printf("      MerkleTree measures leaf-to-root path update (O(log n)).\n");
    return 0;
}
