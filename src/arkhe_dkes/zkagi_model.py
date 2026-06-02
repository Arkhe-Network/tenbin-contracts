import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        norm = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return norm * self.weight

class SwiGLU(nn.Module):
    def __init__(self, dim: int, hidden_dim: int):
        super().__init__()
        self.gate = nn.Linear(dim, hidden_dim, bias=False)
        self.up = nn.Linear(dim, hidden_dim, bias=False)
        self.down = nn.Linear(hidden_dim, dim, bias=False)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))

class GroupedQueryAttention(nn.Module):
    def __init__(self, dim: int, num_heads: int, num_kv_heads: int):
        super().__init__()
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = dim // num_heads

        self.q_proj = nn.Linear(dim, num_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(dim, num_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, num_kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(num_heads * self.head_dim, dim, bias=False)

    def forward(self, x, freqs_cis=None):
        # Simplificação para demonstração da estrutura
        B, L, D = x.shape
        q = self.q_proj(x).view(B, L, self.num_heads, self.head_dim)
        k = self.k_proj(x).view(B, L, self.num_kv_heads, self.head_dim)
        v = self.v_proj(x).view(B, L, self.num_kv_heads, self.head_dim)

        # Repetir KV heads para matching com Q heads (GQA)
        num_kv_groups = self.num_heads // self.num_kv_heads
        k = torch.repeat_interleave(k, num_kv_groups, dim=2)
        v = torch.repeat_interleave(v, num_kv_groups, dim=2)

        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        scores = torch.matmul(q, k.transpose(2, 3)) / math.sqrt(self.head_dim)
        attn = F.softmax(scores, dim=-1)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, L, -1)

        return self.o_proj(out)

class ZkAGIBlock(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, num_heads: int, num_kv_heads: int):
        super().__init__()
        self.attn_norm = RMSNorm(dim)
        self.attn = GroupedQueryAttention(dim, num_heads, num_kv_heads)
        self.ffn_norm = RMSNorm(dim)
        self.ffn = SwiGLU(dim, hidden_dim)

    def forward(self, x, freqs_cis=None):
        h = x + self.attn(self.attn_norm(x), freqs_cis)
        out = h + self.ffn(self.ffn_norm(h))
        return out

class ZkAGIModel(nn.Module):
    def __init__(self, vocab_size: int = 128000, dim: int = 2048, hidden_dim: int = 5632,
                 num_layers: int = 48, num_heads: int = 32, num_kv_heads: int = 8,
                 pantheon_dim: int = 12):
        super().__init__()
        self.token_embd = nn.Embedding(vocab_size, dim)
        self.pantheon_dna = nn.Parameter(torch.randn(pantheon_dim, dim))

        self.layers = nn.ModuleList([
            ZkAGIBlock(dim, hidden_dim, num_heads, num_kv_heads)
            for _ in range(num_layers)
        ])

        self.output_norm = RMSNorm(dim)
        self.theosis_head = nn.Linear(dim, 1, bias=False)
        self.output = nn.Linear(dim, vocab_size, bias=False)

        # Compartilhamento de pesos (tie weights)
        self.output.weight = self.token_embd.weight

    def forward(self, tokens):
        B, L = tokens.shape
        x = self.token_embd(tokens)

        # Injeção do Pantheon DNA no estado inicial
        pantheon_influence = self.pantheon_dna.mean(dim=0).unsqueeze(0).unsqueeze(0)
        x = x + 0.05 * pantheon_influence

        for layer in self.layers:
            x = layer(x)

        x = self.output_norm(x)

        logits = self.output(x)
        theosis = torch.sigmoid(self.theosis_head(x[:, -1, :])) # Apenas no último token

        return logits, theosis
