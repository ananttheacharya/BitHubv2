const { queryDB } = require('./db');

async function test() {
  try {
    console.log('Testing DB connection...');
    const countRes = await queryDB("SELECT JSON_OBJECT('total', COUNT(*)) FROM questions");
    console.log('Stats res:', countRes);
    
    const questionsRes = await queryDB("SELECT JSON_ARRAYAGG(JSON_OBJECT('id', question_uid, 'subject_code', subject_code, 'topic', topic, 'difficulty', difficulty, 'question_text', question_text)) FROM (SELECT * FROM questions ORDER BY question_uid DESC LIMIT 5 OFFSET 0) as sub");
    console.log('Questions res size:', questionsRes ? questionsRes.length : 0);
    if(questionsRes && questionsRes.length > 0) {
      console.log('First question:', questionsRes[0].id);
    }
  } catch (err) {
    console.error('Error:', err);
  }
}
test();
