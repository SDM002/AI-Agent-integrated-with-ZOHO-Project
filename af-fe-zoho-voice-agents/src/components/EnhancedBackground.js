"use client";

import { motion, useMotionValue, useSpring } from "motion/react";
import { useEffect, useState } from "react";

export function EnhancedBackground({ theme }) {
  const [mounted, setMounted] = useState(false);
  const [particles, setParticles] = useState([]);

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springX = useSpring(mouseX, { stiffness: 50, damping: 30 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 30 });

  useEffect(() => {
    setMounted(true);

    // Generate grid particles only on client
    const generatedParticles = Array.from({ length: 40 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      delay: Math.random() * 5,
      duration: 15 + Math.random() * 25,
    }));
    setParticles(generatedParticles);

    const handleMouseMove = (e) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  if (!mounted) return <div className="fixed inset-0 bg-transparent" />;

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Base Gradient */}
      {theme === "light" ? (
        <div className="absolute inset-0 bg-gradient-to-br from-white via-blue-50/20 to-purple-50/10" />
      ) : (
        <div className="absolute inset-0 bg-gradient-to-br from-[#060913] via-[#0a0e1a] to-[#0d1424]" />
      )}

      {/* Animated gradient orbs */}
      <motion.div
        className={`absolute -top-1/4 -left-1/4 w-[900px] h-[900px] rounded-full ${theme === "light" ? "opacity-20" : "opacity-15"
          }`}
        style={{
          background: theme === "light"
            ? "radial-gradient(circle, rgba(0,120,215,0.2) 0%, rgba(0,217,255,0.1) 40%, transparent 70%)"
            : "radial-gradient(circle, rgba(0,120,215,0.5) 0%, rgba(0,217,255,0.2) 40%, transparent 70%)",
          filter: "blur(100px)",
        }}
        animate={{
          x: [0, 120, 0],
          y: [0, 60, 0],
          scale: [1, 1.15, 1],
        }}
        transition={{
          duration: 25,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      <motion.div
        className={`absolute -bottom-1/4 -right-1/4 w-[700px] h-[700px] rounded-full ${theme === "light" ? "opacity-15" : "opacity-12"
          }`}
        style={{
          background: theme === "light"
            ? "radial-gradient(circle, rgba(168,85,247,0.15) 0%, rgba(139,92,246,0.08) 40%, transparent 70%)"
            : "radial-gradient(circle, rgba(168,85,247,0.5) 0%, rgba(139,92,246,0.2) 40%, transparent 70%)",
          filter: "blur(100px)",
        }}
        animate={{
          x: [0, -100, 0],
          y: [0, -70, 0],
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 30,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Cursor-reactive glow */}
      <motion.div
        className="absolute w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{
          left: springX,
          top: springY,
          x: "-50%",
          y: "-50%",
          background: theme === "light"
            ? "radial-gradient(circle, rgba(0,120,215,0.08) 0%, transparent 60%)"
            : "radial-gradient(circle, rgba(0,120,215,0.15) 0%, transparent 60%)",
          filter: "blur(60px)",
        }}
      />

      {/* Enhanced Grid with cursor reaction */}
      <svg className="absolute inset-0 w-full h-full opacity-100">
        <defs>
          <pattern
            id="grid-pattern"
            width="60"
            height="60"
            patternUnits="userSpaceOnUse"
          >
            <motion.path
              d="M 60 0 L 0 0 0 60"
              fill="none"
              stroke={theme === "light" ? "rgba(0,120,215,0.12)" : "rgba(0,120,215,0.15)"}
              strokeWidth="1"
            />
          </pattern>

          <radialGradient id="grid-fade">
            <stop offset="0%" stopColor="white" stopOpacity={theme === "light" ? "0.6" : "0.3"} />
            <stop offset="50%" stopColor="white" stopOpacity={theme === "light" ? "0.3" : "0.15"} />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>
        </defs>

        <motion.rect
          width="100%"
          height="100%"
          fill="url(#grid-pattern)"
          mask="url(#grid-fade)"
        />
      </svg>

      {/* Floating particles with depth */}
      <svg className="absolute inset-0 w-full h-full">
        <defs>
          <radialGradient id="particle-gradient-enhanced">
            <stop offset="0%" stopColor="#0078D7" stopOpacity={theme === "light" ? "0.8" : "1"} />
            <stop offset="50%" stopColor="#00d9ff" stopOpacity={theme === "light" ? "0.4" : "0.6"} />
            <stop offset="100%" stopColor="#00d9ff" stopOpacity="0" />
          </radialGradient>
        </defs>
        {particles.map((particle) => (
          <motion.circle
            key={particle.id}
            cx={`${particle.x}%`}
            cy={`${particle.y}%`}
            r="2"
            fill="url(#particle-gradient-enhanced)"
            initial={{ opacity: 0 }}
            animate={{
              opacity: theme === "light" ? [0, 0.5, 0] : [0, 0.8, 0],
              cy: [`${particle.y}%`, `${(particle.y + 40) % 100}%`],
              r: [1.5, 3, 1.5],
            }}
            transition={{
              duration: particle.duration,
              repeat: Infinity,
              delay: particle.delay,
              ease: "linear",
            }}
          />
        ))}
      </svg>

      {/* Bottom light bloom (dark mode) */}
      {theme === "dark" && (
        <motion.div
          className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[1200px] h-[400px]"
          style={{
            background: "radial-gradient(ellipse at center, rgba(0,120,215,0.15) 0%, transparent 70%)",
            filter: "blur(80px)",
          }}
          animate={{
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      )}

      {/* Radial glow behind orb area (light mode) */}
      {theme === "light" && (
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px]"
          style={{
            background: "radial-gradient(circle, rgba(0,120,215,0.1) 0%, transparent 60%)",
            filter: "blur(60px)",
          }}
        />
      )}

      {/* Ambient light layer */}
      <motion.div
        className="absolute inset-0"
        style={{
          background: theme === "light"
            ? "radial-gradient(circle at 30% 40%, rgba(0,120,215,0.03) 0%, transparent 50%)"
            : "radial-gradient(circle at 30% 40%, rgba(0,120,215,0.08) 0%, transparent 50%)",
        }}
        animate={{
          opacity: [0.5, 1, 0.5],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </div>
  );
}
