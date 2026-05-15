import { useEffect, useRef } from "react";

interface CollectionStar {
  id: string;
  name: string;
  nx: number;
  ny: number;
  x: number;
  y: number;
  r: number;
  phase: number;
  blinkSpeed: number;
  alpha: number;
}

interface BgStar {
  x: number;
  y: number;
  r: number;
  phase: number;
  blinkSpeed: number;
  drift: number;
  color: [number, number, number];
}

interface Shooter {
  x: number;
  y: number;
  vx: number;
  vy: number;
  alpha: number;
  tail: { x: number; y: number }[];
}

interface StarfieldCollectionsEvent {
  collections: { id: string; name: string }[];
}

function randPos(existing: { nx: number; ny: number }[]): {
  nx: number;
  ny: number;
} {
  const minDist = 0.18;
  for (let attempt = 0; attempt < 60; attempt++) {
    const nx =
      Math.random() < 0.5
        ? 0.04 + Math.random() * 0.22
        : 0.74 + Math.random() * 0.22;
    const ny = 0.06 + Math.random() * 0.88;
    const ok = existing.every((s) => {
      const dx = s.nx - nx;
      const dy = s.ny - ny;
      return Math.sqrt(dx * dx + dy * dy) > minDist;
    });
    if (ok) return { nx, ny };
  }
  return { nx: 0.05 + Math.random() * 0.9, ny: 0.05 + Math.random() * 0.9 };
}

export default function StarfieldCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const el: HTMLCanvasElement = canvas;
    const ctx = el.getContext("2d")!;

    let W = 0;
    let H = 0;
    let bgStars: BgStar[] = [];
    let collectionStars: CollectionStar[] = [];
    let shooters: Shooter[] = [];
    let animId: number;

    function setCollections(cols: { id: string; name: string }[]) {
      const existing: { nx: number; ny: number }[] = [];
      collectionStars = cols.map((col) => {
        const prev = collectionStars.find((s) => s.id === col.id);
        if (prev) {
          existing.push({ nx: prev.nx, ny: prev.ny });
          return { ...prev, name: col.name };
        }
        const { nx, ny } = randPos(existing);
        existing.push({ nx, ny });
        return {
          id: col.id,
          name: col.name,
          nx,
          ny,
          x: nx * W,
          y: ny * H,
          r: 3.2 + Math.random() * 1.4,
          phase: Math.random() * Math.PI * 2,
          blinkSpeed: 0.016 + Math.random() * 0.012,
          alpha: 0,
        };
      });
    }

    function handleCollectionsEvent(e: Event) {
      const detail = (e as CustomEvent<StarfieldCollectionsEvent>).detail;
      setCollections(detail.collections);
    }

    window.addEventListener("lm:collections", handleCollectionsEvent);

    function initBgStars() {
      const palette: [number, number, number][] = [
        [170, 150, 255],
        [150, 185, 255],
        [210, 205, 255],
        [200, 200, 255],
        [180, 160, 255],
      ];
      bgStars = Array.from({ length: 420 }, () => {
        const layer = Math.floor(Math.random() * 3);
        return {
          x: Math.random() * W,
          y: Math.random() * H,
          r: 0.1 + Math.random() * (0.3 + layer * 0.28),
          phase: Math.random() * Math.PI * 2,
          blinkSpeed: 0.003 + Math.random() * 0.014,
          drift: 0.001 + Math.random() * (0.004 + layer * 0.005),
          color: palette[Math.floor(Math.random() * palette.length)],
        };
      });
    }

    function drawBgStars() {
      bgStars.forEach((s) => {
        s.y -= s.drift;
        if (s.y < -2) {
          s.y = H + 2;
          s.x = Math.random() * W;
        }
        s.phase += s.blinkSpeed;
        const blink = (Math.sin(s.phase) + 1) / 2;
        const alpha = 0.06 + blink * 0.6;
        const [r, g, b] = s.color;
        if (s.r > 0.4) {
          const gr = s.r * (2.5 + blink * 2.5);
          const gg = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, gr);
          gg.addColorStop(0, `rgba(${r},${g},${b},${alpha * 0.2})`);
          gg.addColorStop(1, "rgba(0,0,0,0)");
          ctx.beginPath();
          ctx.arc(s.x, s.y, gr, 0, Math.PI * 2);
          ctx.fillStyle = gg;
          ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r},${g},${b},${Math.min(1, alpha)})`;
        ctx.fill();
      });
    }

    function drawCollectionStars() {
      collectionStars.forEach((s) => {
        if (s.alpha < 1) s.alpha = Math.min(1, s.alpha + 0.012);
        s.phase += s.blinkSpeed;
        const blink = (Math.sin(s.phase) + 1) / 2;
        const a = s.alpha;

        // Outer nebula glow
        const gr1 = s.r * (10 + blink * 8);
        const g1 = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, gr1);
        g1.addColorStop(0, `rgba(201,162,39,${(0.1 + blink * 0.08) * a})`);
        g1.addColorStop(0.5, `rgba(180,140,30,${0.04 * a})`);
        g1.addColorStop(1, "rgba(0,0,0,0)");
        ctx.beginPath();
        ctx.arc(s.x, s.y, gr1, 0, Math.PI * 2);
        ctx.fillStyle = g1;
        ctx.fill();

        // Mid glow
        const gr2 = s.r * (5 + blink * 4);
        const g2 = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, gr2);
        g2.addColorStop(0, `rgba(255,230,120,${(0.55 + blink * 0.3) * a})`);
        g2.addColorStop(1, "rgba(0,0,0,0)");
        ctx.beginPath();
        ctx.arc(s.x, s.y, gr2, 0, Math.PI * 2);
        ctx.fillStyle = g2;
        ctx.fill();

        // Core
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,248,200,${(0.9 + blink * 0.1) * a})`;
        ctx.fill();

        // Cross flares
        const fLen = s.r * (9 + blink * 7);
        const flares: [number, number][] = [
          [1, 0],
          [0, 1],
          [0.707, 0.707],
          [-0.707, 0.707],
        ];
        flares.forEach(([dx, dy], fi) => {
          if (fi > 1 && blink < 0.5) return;
          const fA = (fi > 1 ? blink * 0.35 : 0.55 + blink * 0.3) * a;
          const fg = ctx.createLinearGradient(
            s.x - dx * fLen,
            s.y - dy * fLen,
            s.x + dx * fLen,
            s.y + dy * fLen,
          );
          fg.addColorStop(0, "rgba(255,255,255,0)");
          fg.addColorStop(0.5, `rgba(255,240,160,${fA})`);
          fg.addColorStop(1, "rgba(255,255,255,0)");
          ctx.beginPath();
          ctx.moveTo(s.x - dx * fLen, s.y - dy * fLen);
          ctx.lineTo(s.x + dx * fLen, s.y + dy * fLen);
          ctx.strokeStyle = fg;
          ctx.lineWidth = fi > 1 ? 0.7 : 1.1;
          ctx.stroke();
        });

        // Name label
        ctx.font = '500 11px "Space Grotesk",sans-serif';
        ctx.fillStyle = `rgba(225,210,150,${(0.55 + blink * 0.3) * a})`;
        ctx.textAlign = "left";
        ctx.fillText(s.name, s.x + s.r * 5 + 8, s.y + 4);
      });
    }

    function spawnShooter() {
      if (Math.random() < 0.0012 && shooters.length < 2) {
        shooters.push({
          x: Math.random() * W * 0.7,
          y: Math.random() * H * 0.4,
          vx: 4 + Math.random() * 5,
          vy: 1.5 + Math.random() * 2.5,
          alpha: 1,
          tail: [],
        });
      }
    }

    function drawShooters() {
      shooters = shooters.filter((s) => s.alpha > 0);
      shooters.forEach((s) => {
        s.tail.push({ x: s.x, y: s.y });
        if (s.tail.length > 24) s.tail.shift();
        s.x += s.vx;
        s.y += s.vy;
        s.alpha -= 0.032;
        s.tail.forEach((pt, i) => {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 0.6, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(215,205,255,${(i / s.tail.length) * s.alpha * 0.5})`;
          ctx.fill();
        });
        ctx.beginPath();
        ctx.arc(s.x, s.y, 1.3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,252,255,${s.alpha})`;
        ctx.fill();
      });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      drawBgStars();
      drawCollectionStars();
      spawnShooter();
      drawShooters();
      animId = requestAnimationFrame(draw);
    }

    function resize() {
      W = el.width = window.innerWidth;
      H = el.height = window.innerHeight;
      initBgStars();
      collectionStars.forEach((s) => {
        s.x = s.nx * W;
        s.y = s.ny * H;
      });
    }

    window.addEventListener("resize", resize);
    resize();
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("lm:collections", handleCollectionsEvent);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        opacity: 0.7,
      }}
    />
  );
}
