"use client";

import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { useEffect, useState } from "react";

export function EnhancedAIOrb({ state, theme }) {
  const [isHovered, setIsHovered] = useState(false);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springX = useSpring(mouseX, { stiffness: 100, damping: 30 });
  const springY = useSpring(mouseY, { stiffness: 100, damping: 30 });

  const rotateX = useTransform(springY, [-300, 300], [5, -5]);
  const rotateY = useTransform(springX, [-300, 300], [-5, 5]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      const rect = document.getElementById("ai-orb")?.getBoundingClientRect();
      if (rect) {
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        mouseX.set(e.clientX - centerX);
        mouseY.set(e.clientY - centerY);
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  const glowIntensity = state === "listening" ? 1.4 : state === "speaking" ? 1.7 : isHovered ? 1.2 : 1;
  const pulseSpeed = state === "listening" ? 1.2 : state === "speaking" ? 0.7 : 2.5;

  return (
    <motion.div
      id="ai-orb"
      className="relative flex items-center justify-center"
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      style={{
        rotateX,
        rotateY,
        transformStyle: "preserve-3d",
      }}
      whileHover={{ scale: 1.05 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      {/* Outer rings with enhanced glow */}
      {[0, 1, 2, 3].map((index) => (
        <motion.div
          key={index}
          className={`absolute rounded-full ${theme === "dark" ? "border-white/5" : "border-[#0078D7]/10"
            }`}
          style={{
            width: 340 + index * 90,
            height: 340 + index * 90,
            borderWidth: index === 0 ? 2 : 1,
            boxShadow: theme === "dark"
              ? `0 0 ${20 + index * 10}px rgba(0,120,215,${0.15 / (index + 1)})`
              : `0 0 ${20 + index * 10}px rgba(0,120,215,${0.1 / (index + 1)})`,
          }}
          animate={{
            opacity: theme === "dark" ? [0.15, 0.35, 0.15] : [0.3, 0.6, 0.3],
            scale: [1, 1.03, 1],
            rotate: index % 2 === 0 ? [0, 360] : [360, 0],
          }}
          transition={{
            opacity: {
              duration: pulseSpeed * 2,
              repeat: Infinity,
              delay: index * 0.3,
              ease: "easeInOut",
            },
            scale: {
              duration: pulseSpeed * 2,
              repeat: Infinity,
              delay: index * 0.3,
              ease: "easeInOut",
            },
            rotate: {
              duration: 40 + index * 10,
              repeat: Infinity,
              ease: "linear",
            },
          }}
        />
      ))}

      {/* Main Orb with mesh effect */}
      <motion.div
        className="relative w-72 h-72 rounded-full overflow-hidden"
        style={{
          background: theme === "dark"
            ? "radial-gradient(circle at 35% 35%, rgba(0,217,255,0.5) 0%, rgba(0,120,215,0.7) 30%, rgba(0,80,160,0.9) 60%, rgba(0,40,100,1) 100%)"
            : "radial-gradient(circle at 35% 35%, rgba(100,220,255,0.8) 0%, rgba(0,180,255,0.9) 30%, rgba(0,120,215,1) 60%, rgba(0,80,160,1) 100%)",
          boxShadow: theme === "dark"
            ? `
              0 0 80px rgba(0,120,215,${0.6 * glowIntensity}),
              0 0 140px rgba(0,120,215,${0.4 * glowIntensity}),
              0 20px 80px rgba(0,0,0,0.3),
              inset 0 0 80px rgba(0,217,255,${0.3 * glowIntensity})
            `
            : `
              0 0 80px rgba(0,120,215,${0.5 * glowIntensity}),
              0 0 120px rgba(0,120,215,${0.3 * glowIntensity}),
              0 30px 80px rgba(0,120,215,${0.35 * glowIntensity}),
              inset 0 0 80px rgba(0,217,255,${0.4 * glowIntensity})
            `,
        }}
        animate={{
          scale: [1, 1.015, 1],
          boxShadow: theme === "dark"
            ? [
              `0 0 80px rgba(0,120,215,${0.6 * glowIntensity}), 0 0 140px rgba(0,120,215,${0.4 * glowIntensity}), 0 20px 80px rgba(0,0,0,0.3), inset 0 0 80px rgba(0,217,255,${0.3 * glowIntensity})`,
              `0 0 100px rgba(0,120,215,${0.8 * glowIntensity}), 0 0 180px rgba(0,120,215,${0.6 * glowIntensity}), 0 20px 100px rgba(0,0,0,0.4), inset 0 0 100px rgba(0,217,255,${0.5 * glowIntensity})`,
              `0 0 80px rgba(0,120,215,${0.6 * glowIntensity}), 0 0 140px rgba(0,120,215,${0.4 * glowIntensity}), 0 20px 80px rgba(0,0,0,0.3), inset 0 0 80px rgba(0,217,255,${0.3 * glowIntensity})`,
            ]
            : [
              `0 0 80px rgba(0,120,215,${0.5 * glowIntensity}), 0 0 120px rgba(0,120,215,${0.3 * glowIntensity}), 0 30px 80px rgba(0,120,215,${0.35 * glowIntensity}), inset 0 0 80px rgba(0,217,255,${0.4 * glowIntensity})`,
              `0 0 100px rgba(0,120,215,${0.7 * glowIntensity}), 0 0 160px rgba(0,120,215,${0.5 * glowIntensity}), 0 30px 100px rgba(0,120,215,${0.45 * glowIntensity}), inset 0 0 100px rgba(0,217,255,${0.6 * glowIntensity})`,
              `0 0 80px rgba(0,120,215,${0.5 * glowIntensity}), 0 0 120px rgba(0,120,215,${0.3 * glowIntensity}), 0 30px 80px rgba(0,120,215,${0.35 * glowIntensity}), inset 0 0 80px rgba(0,217,255,${0.4 * glowIntensity})`,
            ],
        }}
        transition={{
          duration: pulseSpeed,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        {/* Inner core glow - breathing effect */}
        <motion.div
          className="absolute inset-10 rounded-full"
          style={{
            background: theme === "dark"
              ? "radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(200,240,255,0.6) 30%, transparent 70%)"
              : "radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(220,245,255,0.8) 30%, transparent 70%)",
          }}
          animate={{
            opacity: theme === "dark" ? [0.4, 0.65, 0.4] : [0.5, 0.75, 0.5],
            scale: [0.85, 1.05, 0.85],
          }}
          transition={{
            duration: pulseSpeed * 1.8,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        {/* Mesh/Wave surface texture */}
        <svg className="absolute inset-0 w-full h-full opacity-30">
          <defs>
            <pattern id="mesh-pattern" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <motion.path
                d="M0,20 Q10,10 20,20 T40,20 M20,0 Q10,10 20,20 T20,40"
                stroke="rgba(255,255,255,0.4)"
                strokeWidth="0.5"
                fill="none"
                animate={{
                  d: [
                    "M0,20 Q10,10 20,20 T40,20 M20,0 Q10,10 20,20 T20,40",
                    "M0,20 Q10,30 20,20 T40,20 M20,0 Q30,10 20,20 T20,40",
                    "M0,20 Q10,10 20,20 T40,20 M20,0 Q10,10 20,20 T20,40",
                  ],
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              />
            </pattern>
          </defs>
          <circle cx="50%" cy="50%" r="130" fill="url(#mesh-pattern)" />
        </svg>

        {/* Flowing internal particles */}
        {Array.from({ length: 12 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1.5 h-1.5 rounded-full"
            style={{
              background: "radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(0,217,255,0.8) 50%, transparent 100%)",
              top: "50%",
              left: "50%",
              boxShadow: "0 0 8px rgba(255,255,255,0.8), 0 0 16px rgba(0,217,255,0.6)",
            }}
            animate={{
              x: [
                0,
                Math.cos((i * Math.PI * 2) / 12) * 100,
                Math.cos(((i + 6) * Math.PI * 2) / 12) * 100,
                0,
              ],
              y: [
                0,
                Math.sin((i * Math.PI * 2) / 12) * 100,
                Math.sin(((i + 6) * Math.PI * 2) / 12) * 100,
                0,
              ],
              scale: [1, 1.5, 1, 1],
              opacity: [0.6, 1, 0.6, 0.6],
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: "linear",
              delay: i * 0.3,
            }}
          />
        ))}

        {/* Ripple effect for active state */}
        {(state === "speaking" || state === "listening") && (
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-white/40"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{
              scale: [0.8, 1.3],
              opacity: [0.6, 0],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        )}
      </motion.div>

      {/* Waveform for speaking state */}
      {state === "speaking" && (
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-40 flex gap-1.5 items-end">
          {Array.from({ length: 24 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-1 bg-gradient-to-t from-[#0078D7] to-[#00d9ff] rounded-full shadow-lg"
              style={{
                boxShadow: "0 0 8px rgba(0,217,255,0.6)",
              }}
              animate={{
                height: [10, Math.random() * 50 + 25, 10],
              }}
              transition={{
                duration: 0.4,
                repeat: Infinity,
                delay: i * 0.04,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      )}

    </motion.div>
  );
}
