import React, { useState } from 'react';
import { motion } from 'motion/react';

interface LoginProps {
  onLogin: () => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username && password) {
      onLogin();
    }
  };

  return (
    <div className="min-h-screen bg-[#F0F2F5] flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full bg-white rounded-lg shadow-xl overflow-hidden border border-border"
      >
        <div className="bg-navy p-8 text-center border-b-4 border-gold-kserc">
          <div className="flex justify-center gap-4 mb-6">
            <div className="h-16 w-16 bg-white/10 rounded-full flex items-center justify-center border border-white/20">
              <span className="text-[12px] font-bold text-gold-kserc text-center leading-tight uppercase">KSERC<br/>LOGO</span>
            </div>
            <div className="h-16 w-16 bg-white/10 rounded-full flex items-center justify-center border border-white/20">
              <span className="text-[12px] font-bold text-gold-kserc text-center leading-tight uppercase">RIET<br/>LOGO</span>
            </div>
          </div>
          <h1 className="font-serif text-xl font-bold text-white tracking-wide">
            Kerala State Electricity Regulatory Commission
          </h1>
          <p className="text-[#A8C0D8] text-sm mt-2">AI Truing-Up Analysis Tool</p>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-navy">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full p-3 border border-border rounded-md focus:outline-none focus:border-blue-kserc focus:ring-2 focus:ring-blue-kserc/10 transition-all"
              placeholder="Enter your username"
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-semibold text-navy">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 border border-border rounded-md focus:outline-none focus:border-blue-kserc focus:ring-2 focus:ring-blue-kserc/10 transition-all"
              placeholder="Enter your password"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-blue-kserc text-white font-bold py-3 rounded-md shadow-lg hover:bg-[#174E8C] transition-all uppercase tracking-widest text-sm"
          >
            Login to KSERC Portal
          </button>

          <p className="text-center text-[11px] text-[#7A8A99] pt-4 border-t border-border">
            Authorized access only. Work Order KSERC/CSO/03-05
          </p>
        </form>
      </motion.div>
    </div>
  );
}
