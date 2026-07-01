const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const { queryDB } = require('./db');

// In-memory state for managed processes and config
let config = {
  repoPath: path.resolve(__dirname, '..')
};

let processes = {
  frontend: null,
  ngrok: null
};

// --- Config Routes ---
router.get('/config', (req, res) => {
  res.json(config);
});

router.post('/config', (req, res) => {
  if (req.body.repoPath) {
    if (fs.existsSync(req.body.repoPath)) {
      config.repoPath = req.body.repoPath;
      res.json({ success: true, config });
    } else {
      res.status(400).json({ error: 'Path does not exist' });
    }
  } else {
    res.status(400).json({ error: 'repoPath is required' });
  }
});

// --- Process Management Routes ---
router.get('/status', (req, res) => {
  res.json({
    frontend: processes.frontend !== null,
    ngrok: processes.ngrok !== null,
    repoPath: config.repoPath
  });
});

router.post('/process/:name/:action', (req, res) => {
  const { name, action } = req.params;

  if (action === 'start') {
    if (processes[name]) {
      return res.status(400).json({ error: `${name} is already running` });
    }

    if (name === 'frontend') {
      const fePath = path.join(config.repoPath, 'Front-End New');
      processes.frontend = spawn(/^win/.test(process.platform) ? 'npm.cmd' : 'npm', ['run', 'dev'], { cwd: fePath, shell: true });
      
      processes.frontend.on('close', () => { processes.frontend = null; });
      return res.json({ success: true, message: 'Frontend started' });
    } else if (name === 'ngrok') {
      const fePath = path.join(config.repoPath, 'Front-End New');
      processes.ngrok = spawn(/^win/.test(process.platform) ? 'npm.cmd' : 'npm', ['run', 'tunnel'], { cwd: fePath, shell: true });
      
      processes.ngrok.on('close', () => { processes.ngrok = null; });
      return res.json({ success: true, message: 'Ngrok started' });
    } else {
      return res.status(400).json({ error: 'Unknown process' });
    }
  } else if (action === 'stop') {
    if (!processes[name]) {
      return res.status(400).json({ error: `${name} is not running` });
    }

    if (/^win/.test(process.platform)) {
      spawn("taskkill", ["/pid", processes[name].pid, '/f', '/t'], { shell: true });
    } else {
      processes[name].kill();
    }
    
    processes[name] = null;
    return res.json({ success: true, message: `${name} stopped` });
  }

  res.status(400).json({ error: 'Invalid action' });
});

// --- Upload Route ---
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const { semester, subject, type, module } = req.body;
    let destPath = path.join(config.repoPath, 'Study Material');
    
    if (type === 'notes') {
      destPath = path.join(destPath, subject, `MOD${module}`);
    } else if (type === 'pyq') {
      destPath = path.join(destPath, subject, 'QPA'); 
    } else if (type === 'reference') {
      destPath = path.join(destPath);
    }
    
    fs.mkdirSync(destPath, { recursive: true });
    cb(null, destPath);
  },
  filename: function (req, file, cb) {
    cb(null, file.originalname);
  }
});

const upload = multer({ storage: storage });

router.post('/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  res.json({ success: true, file: req.file.path });
});

// --- DB Explorer Routes ---
router.get('/db/stats', async (req, res) => {
  try {
    const countRes = await queryDB("SELECT JSON_OBJECT('total', COUNT(*)) FROM questions");
    const subjRes = await queryDB("SELECT JSON_ARRAYAGG(JSON_OBJECT('subject', subject_code, 'count', c)) FROM (SELECT subject_code, COUNT(*) as c FROM questions GROUP BY subject_code) as sub");
    
    res.json({
      totalQuestions: countRes && countRes.length > 0 ? countRes[0].total : 0,
      bySubject: subjRes || []
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/db/questions', async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 20;
  const offset = (page - 1) * limit;
  const subject = req.query.subject;
  
  try {
    let query = `SELECT JSON_ARRAYAGG(JSON_OBJECT(
      'id', question_uid, 
      'subject_code', subject_code, 
      'question_type', question_type, 
      'difficulty', difficulty, 
      'question_text', question_text
    )) FROM (SELECT * FROM questions`;
    
    if (subject && subject !== 'all') {
      query += ` WHERE subject_code = '${subject.replace(/'/g, "''")}'`;
    }
    
    query += ` ORDER BY question_uid DESC LIMIT ${limit} OFFSET ${offset}) as sub`;
    
    const results = await queryDB(query);
    res.json(results || []);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
