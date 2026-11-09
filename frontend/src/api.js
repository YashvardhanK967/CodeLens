import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchUserAnalytics(formData) {
  const payload = {
    display_name: formData.display_name.trim() || 'Competitive Programmer',
    codeforces: formData.codeforces.trim() || null,
    leetcode: formData.leetcode.trim() || null,
    codechef: formData.codechef.trim() || null,
    geeksforgeeks: formData.geeksforgeeks.trim() || null,
  };

  const response = await axios.post(`${API_BASE_URL}/api/v1/analyze`, payload, {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 35000, // fetching external platforms can take a few seconds
  });

  return response.data;
}

